from typing import Dict, Any, Optional, Union, List
import re

class TextAnalyzer:
    """Handles text analysis operations like sentiment analysis and text preprocessing"""
    
    def __init__(self):
        # Simple sentiment word lists for basic analysis
        self.positive_words = {
            'good', 'great', 'awesome', 'excellent', 'happy', 'love', 'wonderful', 
            'fantastic', 'nice', 'perfect', 'better', 'best', 'glad', 'pleased'
        }
        
        self.negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'sad', 'hate', 'worst',
            'poor', 'disappointed', 'upset', 'angry', 'worse', 'dislike'
        }

    def analyze_sentiment(self, text: str) -> float:
        """
        Analyze text sentiment returning a float between -1.0 and 1.0
        
        Args:
            text: Input text to analyze
            
        Returns:
            float: Sentiment score (-1.0 to 1.0)
        """
        if not text:
            return 0.0
            
        words = text.lower().split()
        
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        
        total_count = positive_count + negative_count
        
        if total_count == 0:
            return 0.0
            
        return (positive_count - negative_count) / total_count

    def preprocess_text(self, text: str) -> str:
        """Clean and normalize input text"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters keeping alphabets, numbers and spaces
        text = re.sub(r'[^a-z0-9\s]', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text

    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract important keywords from text"""
        # Simple word frequency-based extraction
        # Could be enhanced with more sophisticated methods
        
        words = self.preprocess_text(text).split()
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'is', 'are'}
        words = [word for word in words if word not in stop_words]
        
        # Count word frequencies
        from collections import Counter
        word_freq = Counter(words)
        
        # Get most common words
        keywords = [word for word, _ in word_freq.most_common(max_keywords)]
        
        return keywords

    def analyze_complexity(self, text: str) -> Dict[str, Any]:
        """Analyze text complexity"""
        if not text:
            return {
                "word_count": 0,
                "avg_word_length": 0,
                "sentence_count": 0
            }
            
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        words = text.split()
        
        return {
            "word_count": len(words),
            "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "sentence_count": len(sentences)
        }