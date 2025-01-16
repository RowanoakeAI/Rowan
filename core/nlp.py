from typing import Dict, Any, Optional, Union, List, Tuple
import re
from collections import Counter
import math
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
from langdetect import detect

class TextAnalyzer:
    """Handles text analysis operations like sentiment analysis and text preprocessing"""
    
    def __init__(self):
        # Download required NLTK data
        nltk.download('punkt')
        nltk.download('averaged_perceptron_tagger')
        nltk.download('stopwords')
        
        # Simple sentiment word lists for basic analysis
        self.positive_words = {
            'good', 'great', 'awesome', 'excellent', 'happy', 'love', 'wonderful', 
            'fantastic', 'nice', 'perfect', 'better', 'best', 'glad', 'pleased'
        }
        
        self.negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'sad', 'hate', 'worst',
            'poor', 'disappointed', 'upset', 'angry', 'worse', 'dislike'
        }

        self.intensifiers = {
            'very': 1.5,
            'really': 1.3,
            'extremely': 2.0,
            'totally': 1.4,
            'absolutely': 1.8
        }

        self.emojis = {
            '😊': 1, '😃': 1, '😄': 1, '🙂': 0.5, '😐': 0,
            '😟': -0.5, '😢': -1, '😭': -1, '😡': -1
        }

        self.contractions = {
            "ain't": "is not", "aren't": "are not", "can't": "cannot", 
            "couldn't": "could not", "didn't": "did not", "doesn't": "does not",
            "won't": "will not", "wouldn't": "would not", "hasn't": "has not"
        }

        # Add more sophisticated word lists
        self.stop_words = set(stopwords.words('english'))
        self.entity_patterns = {
            'EMAIL': r'[\w\.-]+@[\w\.-]+\.\w+',
            'PHONE': r'\+?[\d\-\(\) ]{10,}',
            'URL': r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
        }

    def expand_contractions(self, text: str) -> str:
        """Expand contractions in text"""
        for contraction, expansion in self.contractions.items():
            text = text.replace(contraction, expansion)
        return text

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Enhanced sentiment analysis"""
        if not text:
            return {"score": 0.0, "magnitude": 0.0}
            
        # Preprocess
        text = self.expand_contractions(text.lower())
        words = text.split()
        
        score = 0.0
        negation = False
        last_was_intensifier = False
        intensifier_value = 1.0

        for word in words:
            # Handle emojis
            if word in self.emojis:
                score += self.emojis[word]
                continue

            # Handle negation
            if word in {'not', 'no', 'never', "n't"}:
                negation = True
                continue

            # Handle intensifiers
            if word in self.intensifiers:
                intensifier_value = self.intensifiers[word]
                last_was_intensifier = True
                continue

            # Score words
            word_score = 0
            if word in self.positive_words:
                word_score = 1
            elif word in self.negative_words:
                word_score = -1

            if word_score != 0:
                if negation:
                    word_score *= -1
                    negation = False
                if last_was_intensifier:
                    word_score *= intensifier_value
                    last_was_intensifier = False
                    intensifier_value = 1.0
                score += word_score

        # Add magnitude calculation
        magnitude = abs(score) * (1 + len([w for w in words if w in self.intensifiers]))
        
        return {
            "score": max(min(score, 1.0), -1.0),
            "magnitude": min(magnitude, 2.0)
        }

    def preprocess_text(self, text: str) -> str:
        """Enhanced text preprocessing"""
        # Expand contractions
        text = self.expand_contractions(text.lower())
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text)
        
        # Remove emails
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove special characters keeping alphabets, numbers and spaces
        text = re.sub(r'[^a-z0-9\s]', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text

    def extract_keywords(self, text: str, max_keywords: int = 5, include_bigrams: bool = True) -> List[str]:
        """Enhanced keyword extraction using TF-IDF-like scoring"""
        processed_text = self.preprocess_text(text)
        words = processed_text.split()
        
        # Generate word frequencies
        word_freq = Counter(words)
        
        # Generate bigrams if requested
        if include_bigrams and len(words) > 1:
            bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
            word_freq.update(Counter(bigrams))
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'is', 'are'}
        word_freq = {k: v for k, v in word_freq.items() if k not in stop_words}
        
        # Calculate score considering word length and frequency
        scores = {}
        max_freq = max(word_freq.values())
        for word, freq in word_freq.items():
            term_freq = freq / max_freq
            length_factor = math.log(len(word) + 1)
            scores[word] = term_freq * length_factor
        
        # Get top keywords
        keywords = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [word for word, score in keywords[:max_keywords]]

    def analyze_complexity(self, text: str) -> Dict[str, Any]:
        """Enhanced text complexity analysis"""
        if not text:
            return {
                "word_count": 0,
                "avg_word_length": 0,
                "sentence_count": 0,
                "vocabulary_richness": 0,
                "avg_sentence_length": 0
            }
            
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        words = text.split()
        unique_words = set(words)
        
        return {
            "word_count": len(words),
            "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "sentence_count": len(sentences),
            "vocabulary_richness": len(unique_words) / len(words) if words else 0,
            "avg_sentence_length": len(words) / len(sentences) if sentences else 0
        }

    def calculate_readability(self, text: str) -> Dict[str, float]:
        """Calculate readability metrics"""
        if not text:
            return {"flesch_score": 0.0, "fog_index": 0.0}
            
        sentences = sent_tokenize(text)
        words = word_tokenize(text.lower())
        
        # Calculate base metrics
        word_count = len(words)
        sentence_count = len(sentences)
        syllable_count = sum(self._count_syllables(word) for word in words)
        
        # Flesch Reading Ease
        flesch = 206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllable_count / word_count)
        
        # Gunning Fog Index
        complex_words = len([word for word in words if self._count_syllables(word) >= 3])
        fog = 0.4 * ((word_count / sentence_count) + 100 * (complex_words / word_count))
        
        return {
            "flesch_score": round(max(0, min(100, flesch)), 2),
            "fog_index": round(fog, 2)
        }

    def detect_language(self, text: str) -> str:
        """Detect text language"""
        try:
            return detect(text)
        except:
            return 'unknown'
            
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text"""
        entities = {
            'PERSON': [],
            'ORGANIZATION': [],
            'EMAIL': [],
            'URL': []
        }
        
        # Extract pattern-based entities
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                entities[entity_type] = matches
                
        # Extract POS-based entities
        words = word_tokenize(text)
        pos_tags = pos_tag(words)
        
        current_entity = []
        for word, tag in pos_tags:
            if tag.startswith('NNP'):
                current_entity.append(word)
            elif current_entity:
                entities['PERSON'].append(' '.join(current_entity))
                current_entity = []
                
        return entities

    def _count_syllables(self, word: str) -> int:
        """Helper method to count syllables"""
        word = word.lower()
        count = 0
        vowels = 'aeiouy'
        prev_char_is_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_char_is_vowel:
                count += 1
            prev_char_is_vowel = is_vowel
            
        if word.endswith('e'):
            count -= 1
        if count == 0:
            count = 1
        return count