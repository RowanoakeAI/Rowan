from core.module_manager import ModuleInterface
from core.personal_memory import PersonalMemorySystem
from utils.logger import setup_logger
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import re
from typing import Dict, Any, Tuple, List
from datetime import datetime
from modules.notifications.notification_module import NotificationsModule  # Fixed: NotificationModule -> NotificationsModule
import logging
from threading import Timer
from typing import Optional

class EmailModule(ModuleInterface):
    """Email integration module for Rowan"""
    
    COMMAND_PATTERNS = {
        "send": r"(?:can you |please |)(?:send|write|compose).*?(?:email|mail|message)",
        "check": r"(?:can you |please |any new |)(?:check|read|show|get).*?(?:email|mail|inbox)",
        "search": r"(?:can you |please |)(?:find|search|look for).*?(?:email|mail|message)"
    }

    # Add category definitions
    CATEGORIES = {
        "important": {
            "keywords": ["urgent", "important", "asap", "priority", "deadline"],
            "senders": ["boss@company.com", "manager@company.com"],
            "score_threshold": 0.7
        },
        "updates": {
            "keywords": ["newsletter", "update", "announcement", "notification"],
            "senders": ["notifications@", "updates@", "newsletter@"],
            "score_threshold": 0.5
        },
        "spam": {
            "keywords": ["lottery", "winner", "viagra", "investment", "prince", "inheritance"],
            "senders": ["unknown@", "noreply@"],
            "score_threshold": 0.6
        }
        # Regular category is default when no others match
    }

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.memory = PersonalMemorySystem()
        self.imap = None
        self.smtp = None
        self.initialized = False
        self.notification_module = None
        self.command_handlers = {
            "send": self._handle_send,
            "check": self._handle_check,
            "search": self._handle_search
        }
        self.logger = logging.getLogger(__name__)
        self.check_timer: Optional[Timer] = None
        self.check_interval = 300  # 5 minutes default

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize email connections and notification system"""
        try:
            # Setup IMAP for receiving
            self.imap = imaplib.IMAP4_SSL(config["imap_server"])
            self.imap.login(config["email"], config["password"])
            
            # Setup SMTP for sending
            self.smtp = smtplib.SMTP_SSL(config["smtp_server"])
            self.smtp.login(config["email"], config["password"])
            
            # Initialize notification module reference
            self.notification_module = config.get("notification_module")
            
            self.initialized = True
            self.logger.info("Email module initialized successfully")
            
            if config.get("enable_periodic_check", True):
                interval = config.get("check_interval", 300)
                self.start_periodic_check(interval)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize email: {str(e)}")
            return False

    def _handle_send(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email sending commands"""
        try:
            # Extract recipient, subject, and content from input
            recipient = self._extract_recipient(input_text)
            subject = self._extract_subject(input_text)
            content = self._extract_content(input_text)
            
            if not all([recipient, subject, content]):
                return {
                    "success": False,
                    "response": "I need a recipient, subject, and content to send an email. Could you provide those?"
                }
                
            # Create email
            msg = MIMEMultipart()
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(content, "plain"))
            
            # Send email
            self.smtp.send_message(msg)
            
            # Store in memory
            self.memory.store_email({
                "to": recipient,
                "subject": subject,
                "content": content,
                "timestamp": datetime.utcnow(),
                "type": "sent"
            })
            
            return {
                "success": True,
                "response": f"I've sent the email to {recipient}."
            }
            
        except Exception as e:
            self.logger.error(f"Error sending email: {str(e)}")
            return {
                "success": False,
                "response": "I encountered an error while trying to send the email."
            }

    def _categorize_email(self, email_obj: email.message.Message) -> Tuple[str, float]:
        """Categorize email based on content analysis and return category with confidence score"""
        
        # Extract email data
        subject = str(decode_header(email_obj["subject"])[0][0])
        sender = email_obj["from"]
        content = self._get_email_content(email_obj)
        
        # Initialize scores for each category
        scores = {
            "important": 0.0,
            "updates": 0.0,
            "spam": 0.0,
            "regular": 0.0
        }

        # Score each category
        for category, rules in self.CATEGORIES.items():
            score = 0.0
            
            # Check subject and content for keywords
            for keyword in rules["keywords"]:
                if keyword.lower() in subject.lower():
                    score += 0.3
                if keyword.lower() in content.lower():
                    score += 0.2
                    
            # Check sender patterns
            for sender_pattern in rules["senders"]:
                if sender_pattern.lower() in sender.lower():
                    score += 0.4
                    
            # Additional spam indicators
            if category == "spam":
                if self._has_spam_indicators(subject, content):
                    score += 0.3
                    
            scores[category] = min(score, 1.0)
            
        # Set regular score based on lack of other matches
        scores["regular"] = 1.0 - max(scores["important"], scores["updates"], scores["spam"])
        
        # Get highest scoring category
        category = max(scores.items(), key=lambda x: x[1])
        return category[0], category[1]

    def _has_spam_indicators(self, subject: str, content: str) -> bool:
        """Check for common spam indicators"""
        spam_indicators = [
            r'\$[\d,]+',  # Dollar amounts
            r'[0-9]{1,2}0%\s(?:off|discount)',  # Large discounts
            r'(?i)free\s+prize',  # Free prizes
            r'(?i)act\s+now',  # Urgency phrases
            r'(?i)limited\s+time',  # Time pressure
        ]
        
        text = f"{subject} {content}".lower()
        return any(re.search(pattern, text) for pattern in spam_indicators)

    def _get_email_content(self, email_obj: email.message.Message) -> str:
        """Extract email content from potentially multipart message"""
        content = ""
        if email_obj.is_multipart():
            for part in email_obj.walk():
                if part.get_content_type() == "text/plain":
                    content += part.get_payload(decode=True).decode()
        else:
            content = email_obj.get_payload(decode=True).decode()
        return content

    def _handle_check(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle email checking with categorization and notifications"""
        try:
            self.imap.select('INBOX')
            _, messages = self.imap.search(None, 'ALL')
            
            categories = {
                "important": [],
                "updates": [],
                "regular": [],
                "spam": []
            }
            
            # Process last 10 emails
            for num in messages[0].split()[-10:]:
                _, msg = self.imap.fetch(num, '(RFC822)')
                email_obj = email.message_from_bytes(msg[0][1])
                category, confidence = self._categorize_email(email_obj)
                
                # Only categorize if confidence meets threshold
                if category != "regular" and confidence < self.CATEGORIES[category]["score_threshold"]:
                    category = "regular"
                    
                email_data = {
                    "subject": str(decode_header(email_obj["subject"])[0][0]),
                    "from": email_obj["from"],
                    "date": email_obj["date"]
                }
                
                categories[category].append(email_data)
                
                # Send notifications based on category
                if category == "important":
                    self.notification_module.send_notification(
                        title="Important Email",
                        message=f"From: {email_data['from']}\nSubject: {email_data['subject']}",
                        timeout=15
                    )
                elif category == "spam":
                    self.notification_module.send_notification(
                        title="Spam Detected",
                        message=f"Spam email detected from {email_data['from']}",
                        timeout=5
                    )
            
            return {
                "success": True,
                "response": self._format_email_summary(categories),
                "categories": categories
            }
            
        except Exception as e:
            self.logger.error(f"Error checking emails: {str(e)}")
            return {
                "success": False,
                "response": "I encountered an error while checking your emails."
            }

    def _format_email_summary(self, categories: Dict[str, list]) -> str:
        """Format categorized emails into a readable summary"""
        summary = []
        for category, emails in categories.items():
            if emails:
                summary.append(f"\n{category.title()} ({len(emails)}):")
                for email in emails:
                    summary.append(f"- From: {email['from']}")
                    summary.append(f"  Subject: {email['subject']}")
                    
        return "\n".join(summary) if summary else "No emails found."

    async def _handle_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Handle email search requests.
        
        Args:
            query (str): Search query string
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of matching email messages
        """
        try:
            self.logger.debug(f"Processing email search request: {query}")
            
            if not query:
                raise ValueError("Search query cannot be empty")
                
            if not hasattr(self, 'gmail_service'):
                raise RuntimeError("Gmail service not initialized")

            # Execute search query
            results = await self.gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = []
            for msg in results.get('messages', []):
                email = await self.gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                messages.append(email)

            self.logger.info(f"Found {len(messages)} matching emails")
            return messages

        except Exception as e:
            self.logger.error(f"Error in email search: {str(e)}")
            raise RuntimeError(f"Email search failed: {str(e)}")

    def start_periodic_check(self, interval: int = 300):
        """Start periodic email checking"""
        self.check_interval = interval
        self.schedule_next_check()
        self.logger.info(f"Started periodic email checking every {interval} seconds")
    
    def schedule_next_check(self):
        """Schedule the next email check"""
        if self.initialized:
            self.check_timer = Timer(self.check_interval, self._periodic_check)
            self.check_timer.daemon = True
            self.check_timer.start()
    
    def _periodic_check(self):
        """Perform periodic email check"""
        try:
            result = self._handle_check("", {})
            if result["success"]:
                self.logger.info("Periodic email check completed")
            else:
                self.logger.error("Periodic email check failed")
        except Exception as e:
            self.logger.error(f"Error in periodic email check: {str(e)}")
        finally:
            self.schedule_next_check()
    
    def stop_periodic_check(self):
        """Stop periodic email checking"""
        if self.check_timer:
            self.check_timer.cancel()
            self.check_timer = None

    def shutdown(self) -> None:
        """Clean shutdown of email module"""
        try:
            self.stop_periodic_check()
            if self.notification_module:
                self.notification_module.stop()
            if self.imap:
                self.imap.logout()
            if self.smtp:
                self.smtp.quit()
        except Exception as e:
            self.logger.error(f"Error during email module shutdown: {str(e)}")