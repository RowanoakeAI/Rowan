# core/personal_memory.py
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta, date
from enum import Enum
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
from utils.logger import setup_logger

class PersonalityTrait(Enum):
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    STABILITY = "stability"

class InteractionContext(Enum):
    CASUAL = "casual"
    PROFESSIONAL = "professional"
    EMOTIONAL = "emotional"
    TASK_ORIENTED = "task_oriented"
    LEARNING = "learning"

class InteractionSource(Enum):
    DISCORD = "discord"
    LOCAL = "local"
    GUI = "gui"
    API = "api"
    UNKNOWN = "unknown"

class ReminderStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"

class PersonalMemorySystem:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", 
                 database_name: str = "Rowan"):
        if not self._initialized:
            self.logger = setup_logger(__name__)
            
            try:
                self.client = MongoClient(connection_string)
                self.db = self.client[database_name]
                
                # Initialize collections
                self.personality = self.db.personality
                self.preferences = self.db.preferences
                self.relationships = self.db.relationships
                self.interactions = self.db.interactions
                self.habits = self.db.habits
                self.goals = self.db.goals
                self.schedule = self.db.schedule
                self.knowledge = self.db.knowledge
                self.feedback = self.db.feedback
                self.media = self.db.media_preferences
                self.calendar_events = self.db.calendar_events
                self.module_states = self.db.module_states  # Add new collection
                self.reminders = self.db.reminders
                
                self._setup_indexes()
                self._initialize_personality()
                
                self.logger.info(f"Successfully connected to database: {database_name}")
                self._initialized = True
                
            except Exception as e:
                self.logger.error(f"Error initializing PersonalMemorySystem: {str(e)}")
                raise
    
    def _setup_indexes(self):
        """Set up MongoDB collection indexes"""
        try:
            # Interactions by time and context
            self.interactions.create_index([
                ("timestamp", pymongo.DESCENDING),
                ("context_type", pymongo.ASCENDING)
            ])
            
            # Preferences by category
            self.preferences.create_index([("category", pymongo.ASCENDING)])
            
            # Goals by priority and deadline
            self.goals.create_index([
                ("priority", pymongo.DESCENDING),
                ("deadline", pymongo.ASCENDING)
            ])
            
            # Schedule by date
            self.schedule.create_index([("date", pymongo.ASCENDING)])
            
            # Knowledge by topic and importance  
            self.knowledge.create_index([
                ("topic", pymongo.ASCENDING),
                ("importance", pymongo.DESCENDING)
            ])
            
            # Reminders by due date and status
            self.reminders.create_index([
                ("due_date", pymongo.ASCENDING),
                ("status", pymongo.ASCENDING)
            ])
            
            self.logger.info("Successfully created database indexes")
            
        except Exception as e:
            self.logger.error(f"Error setting up indexes: {str(e)}")
            raise

    def _initialize_personality(self):
        """Initialize or update personality baseline"""
        if not self.personality.find_one({"type": "baseline"}):
            baseline = {
                "type": "baseline",
                "traits": {
                    trait.value: 0.5 for trait in PersonalityTrait
                },
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow()
            }
            self.personality.insert_one(baseline)

    def update_personality_trait(self, trait: PersonalityTrait, value: float,
                               context: Dict[str, Any]):
        """Update personality trait based on interactions"""
        self.personality.update_one(
            {"type": "baseline"},
            {
                "$set": {
                    f"traits.{trait.value}": value,
                    "last_updated": datetime.utcnow()
                },
                "$push": {
                    "updates": {
                        "trait": trait.value,
                        "value": value,
                        "context": context,
                        "timestamp": datetime.utcnow()
                    }
                }
            }
        )

    def store_preference(self, category: str, item: str, rating: float,
                        context: Dict[str, Any] = None):
        """Store or update a preference"""
        self.preferences.update_one(
            {"category": category, "item": item},
            {
                "$set": {
                    "rating": rating,
                    "last_updated": datetime.utcnow(),
                    "context": context
                },
                "$push": {
                    "history": {
                        "rating": rating,
                        "timestamp": datetime.utcnow(),
                        "context": context
                    }
                }
            },
            upsert=True
        )

    def store_interaction(self, content: Dict[str, Any],
                         context_type: InteractionContext,
                         source: InteractionSource = InteractionSource.UNKNOWN,
                         mood: Optional[str] = None,
                         importance: int = 1):
        """Store an interaction with context and source"""
        document = {
            "content": content,
            "context_type": context_type.value,
            "source": source.value,
            "mood": mood,
            "importance": importance,
            "timestamp": datetime.utcnow(),
            "day_of_week": datetime.utcnow().strftime("%A"),
            "time_of_day": datetime.utcnow().strftime("%H:%M")
        }
        self.interactions.insert_one(document)

    def store_habit(self, name: str, category: str,
                   triggers: List[str], frequency: Dict[str, Any]):
        """Store or update a habit"""
        self.habits.update_one(
            {"name": name},
            {
                "$set": {
                    "category": category,
                    "triggers": triggers,
                    "frequency": frequency,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )

    def set_goal(self, title: str, description: str, deadline: datetime,
                priority: int, milestones: List[Dict[str, Any]] = None):
        """Set a new goal or update existing one"""
        self.goals.update_one(
            {"title": title},
            {
                "$set": {
                    "description": description,
                    "deadline": deadline,
                    "priority": priority,
                    "milestones": milestones or [],
                    "status": "active",
                    "progress": 0,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )

    def update_schedule(self, date: datetime, events: List[Dict[str, Any]]):
        """Update schedule for a specific date"""
        self.schedule.update_one(
            {"date": date.date()},
            {
                "$set": {
                    "events": events,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )

    def store_knowledge(self, topic: str, content: Dict[str, Any],
                       importance: int, source: str = None):
        """Store personal knowledge or information"""
        document = {
            "topic": topic,
            "content": content,
            "importance": importance,
            "source": source,
            "created_at": datetime.utcnow(),
            "last_accessed": datetime.utcnow()
        }
        self.knowledge.insert_one(document)

    def store_feedback(self, interaction_id: str, feedback_type: str,
                      content: Dict[str, Any], rating: int = None):
        """Store feedback about interactions"""
        document = {
            "interaction_id": interaction_id,
            "feedback_type": feedback_type,
            "content": content,
            "rating": rating,
            "timestamp": datetime.utcnow()
        }
        self.feedback.insert_one(document)

    def store_media_preference(self, media_type: str, title: str,
                             rating: float, tags: List[str], review: str = None):
        """Store media preferences and reviews"""
        self.media.update_one(
            {"media_type": media_type, "title": title},
            {
                "$set": {
                    "rating": rating,
                    "tags": tags,
                    "review": review,
                    "last_updated": datetime.utcnow()
                },
                "$push": {
                    "rating_history": {
                        "rating": rating,
                        "timestamp": datetime.utcnow()
                    }
                }
            },
            upsert=True
        )

    def store_calendar_event(self, event_data: Dict[str, Any]) -> bool:
        """Store calendar event in memory"""
        try:
            self.db.calendar_events.update_one(
                {'event_id': event_data['event_id']},
                {'$set': event_data},
                upsert=True
            )
            return True
        except Exception as e:
            self.logger.error(f"Error storing calendar event: {e}")
            return False

    def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming calendar events"""
        try:
            now = datetime.utcnow()
            timeMax = now + timedelta(days=days)
            
            events = self.db.calendar_events.find({
                'start': {'$gte': now, '$lte': timeMax}
            }).sort('start', 1)
            
            return list(events)
        except Exception as e:
            self.logger.error(f"Error retrieving calendar events: {e}")
            return []

    def get_personality_profile(self) -> Dict[str, Any]:
        """Get current personality profile with history"""
        return self.personality.find_one({"type": "baseline"})

    def get_preferences_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all preferences in a category"""
        return list(self.preferences.find({"category": category}))

    def get_recent_interactions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent interactions"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return list(self.interactions.find(
            {"timestamp": {"$gte": cutoff}}
        ).sort("timestamp", pymongo.DESCENDING))

    def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get all active goals"""
        return list(self.goals.find({"status": "active"}).sort("priority", pymongo.DESCENDING))

    def get_schedule_range(self, start_date, end_date):
        """Get schedule items within a date range"""
        # Convert date objects to datetime if necessary
        if isinstance(start_date, date):
            start_date = datetime.combine(start_date, datetime.min.time())
        if isinstance(end_date, date):
            end_date = datetime.combine(end_date, datetime.max.time())
            
        return list(self.schedule.find({
            "date": {
                "$gte": start_date,
                "$lt": end_date
            }
        }).sort("date", pymongo.ASCENDING))

    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze interaction and behavior patterns"""
        # Time-based patterns
        time_patterns = self.interactions.aggregate([
            {
                "$group": {
                    "_id": {
                        "day": "$day_of_week",
                        "hour": {"$substr": ["$time_of_day", 0, 2]}
                    },
                    "count": {"$sum": 1},
                    "average_importance": {"$avg": "$importance"}
                }
            }
        ])
        
        # Mood patterns
        mood_patterns = self.interactions.aggregate([
            {
                "$match": {"mood": {"$exists": True}}
            },
            {
                "$group": {
                    "_id": "$mood",
                    "count": {"$sum": 1},
                    "contexts": {"$addToSet": "$context_type"}
                }
            }
        ])
        
        return {
            "time_patterns": list(time_patterns),
            "mood_patterns": list(mood_patterns)
        }

    def generate_insights(self) -> Dict[str, Any]:
        """Generate insights from stored data"""
        insights = {
            "preference_changes": [],
            "habit_patterns": [],
            "goal_progress": [],
            "interaction_trends": []
        }
        
        # Analyze preference changes
        preference_changes = self.preferences.aggregate([
            {"$unwind": "$history"},
            {"$sort": {"history.timestamp": -1}},
            {"$group": {
                "_id": {
                    "category": "$category",
                    "item": "$item"
                },
                "current_rating": {"$first": "$history.rating"},
                "previous_rating": {"$nth": {"$history.rating": 1}},
                "change_timestamp": {"$first": "$history.timestamp"}
            }},
            {"$match": {
                "$expr": {"$ne": ["$current_rating", "$previous_rating"]}
            }}
        ])
        insights["preference_changes"] = list(preference_changes)
        
        return insights

    def get_module_state(self, module_name: str) -> Dict[str, Any]:
        """Get module state from database"""
        try:
            state = self.module_states.find_one({"module_name": module_name})
            return state if state else None
        except Exception as e:
            self.logger.error(f"Error retrieving module state: {str(e)}")
            return None
            
    def update_module_state(self, module_name: str, state: Dict[str, Any]) -> bool:
        """Update module state in database"""
        try:
            self.module_states.update_one(
                {"module_name": module_name},
                {"$set": {
                    "state": state,
                    "last_updated": datetime.utcnow()
                }},
                upsert=True
            )
            return True
        except Exception as e:
            self.logger.error(f"Error updating module state: {str(e)}")
            return False
            
    def reset_module_state(self, module_name: str) -> bool:
        """Reset module state to default"""
        try:
            self.module_states.delete_one({"module_name": module_name})
            return True
        except Exception as e:
            self.logger.error(f"Error resetting module state: {str(e)}")
            return False

    def create_reminder(self, title: str, due_date: datetime, 
                       description: str = None, priority: int = 1,
                       recurrence: Dict[str, Any] = None) -> str:
        """Create a new reminder"""
        reminder = {
            "title": title,
            "description": description,
            "due_date": due_date,
            "priority": priority,
            "status": ReminderStatus.PENDING.value,
            "created_at": datetime.utcnow(),
            "recurrence": recurrence,
            "modified_at": datetime.utcnow()
        }
        result = self.reminders.insert_one(reminder)
        return str(result.inserted_id)

    def get_upcoming_reminders(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming reminders"""
        now = datetime.utcnow()
        end_date = now + timedelta(days=7)
        
        return list(self.reminders.find({
            "due_date": {"$gte": now, "$lte": end_date},
            "status": ReminderStatus.PENDING.value
        }).sort("due_date", pymongo.ASCENDING))

    def update_reminder_status(self, reminder_id: str, 
                             status: ReminderStatus) -> bool:
        """Update reminder status"""
        try:
            self.reminders.update_one(
                {"_id": ObjectId(reminder_id)},
                {
                    "$set": {
                        "status": status.value,
                        "modified_at": datetime.utcnow()
                    }
                }
            )
            return True
        except Exception as e:
            self.logger.error(f"Error updating reminder status: {e}")
            return False

    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder"""
        try:
            self.reminders.delete_one({"_id": ObjectId(reminder_id)})
            return True
        except Exception as e:
            self.logger.error(f"Error deleting reminder: {e}")
            return False

    def update_reminder(self, reminder_id: str, 
                       updates: Dict[str, Any]) -> bool:
        """Update reminder details"""
        try:
            updates["modified_at"] = datetime.utcnow()
            self.reminders.update_one(
                {"_id": ObjectId(reminder_id)},
                {"$set": updates}
            )
            return True
        except Exception as e:
            self.logger.error(f"Error updating reminder: {e}")
            return False

    def get_time_relevant_context(self) -> Dict[str, Any]:
        """Enhanced time context with more granular patterns"""
        current_time = datetime.now().replace(microsecond=0)
        
        # Enhanced time context
        time_context = {
            "time_of_day": "morning" if 5 <= current_time.hour < 12 else
                          "afternoon" if 12 <= current_time.hour < 17 else
                          "evening" if 17 <= current_time.hour < 22 else
                          "night",
            "day_of_week": current_time.strftime("%A"),
            "is_weekend": current_time.weekday() >= 5,
            "part_of_month": "early" if current_time.day <= 10 else
                            "mid" if current_time.day <= 20 else
                            "late",
            "season": self._get_current_season(current_time),
            "current_time": current_time
        }
        return time_context

    def close(self):
        """Close the MongoDB connection"""
        self.client.close()

    def analyze_interaction_patterns(self) -> Dict[str, Any]:
        """Analyze user interaction patterns"""
        return {
            "time_patterns": self._analyze_time_patterns(),
            "context_patterns": self._analyze_context_patterns(),
            "mood_patterns": self._analyze_mood_patterns(),
            "module_patterns": self._analyze_module_usage()
        }

    def _analyze_context_patterns(self) -> List[Dict[str, Any]]:
        """Analyze common context transitions"""
        pipeline = [
            {"$sort": {"timestamp": 1}},
            {"$group": {
                "_id": "$context_type",
                "count": {"$sum": 1},
                "common_transitions": {"$push": "$next_context"},
                "average_duration": {"$avg": "$duration"}
            }}
        ]
        return list(self.interactions.aggregate(pipeline))