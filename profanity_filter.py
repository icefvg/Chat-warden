import re
import json
import time
import asyncio
import unicodedata
import os
from typing import Tuple, Dict, List, Set
from fuzzywuzzy import fuzz

class ProfanityFilter:
    """Advanced profanity filter with obfuscation detection"""
    
    def __init__(self):
        self.bad_words = {}
        self.replacements = {}
        self.cooldowns = {}
        self.bypass_patterns = []
        
        # Enhanced leetspeak mapping
        self.leetspeak_map = {
            'a': ['a', '@', '4', '*', 'α', 'ä', 'á', 'à', 'â'],
            'e': ['e', '3', '€', 'ε', 'ë', 'é', 'è', 'ê'],
            'i': ['i', '1', '!', 'l', '|', 'ι', 'í', 'ì', 'î', 'ï'],
            'o': ['o', '0', '*', 'ο', 'ö', 'ó', 'ò', 'ô'],
            'u': ['u', 'v', 'μ', 'ü', 'ú', 'ù', 'û'],
            's': ['s', '$', '5', 'ς', 'ş'],
            't': ['t', '7', '+', 'τ'],
            'g': ['g', '9', '6', 'q'],
            'z': ['z', '2'],
            'b': ['b', '6', 'β'],
            'l': ['l', '1', '!', '|', 'ι'],
            'c': ['c', '(', '<', 'ç'],
            'd': ['d', 'cl', 'δ'],
            'f': ['f', 'ph', 'ƒ'],
            'h': ['h', '#'],
            'k': ['k', 'c', '<'],
            'm': ['m', 'rn'],
            'n': ['n', 'r', 'ñ'],
            'p': ['p', 'q'],
            'q': ['q', '9'],
            'r': ['r', 'n'],
            'v': ['v', 'u'],
            'w': ['w', 'vv', 'uu'],
            'x': ['x', '*', '×'],
            'y': ['y', 'j', 'ÿ', 'ý']
        }
        
        # Common separator patterns
        self.separators = r'[\s\.\-_\*\~\!\@\#\$\%\^\&\(\)\+\=\[\]\{\}\|\\\;\:\'\"\,\<\>\/\?]*'
        
        self.load_word_lists()
        self.compile_patterns()
    
    def load_word_lists(self):
        """Load bad words and replacements from JSON files"""
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        try:
            with open('data/bad_words.json', 'r', encoding='utf-8') as f:
                self.bad_words = json.load(f)
        except FileNotFoundError:
            self.bad_words = self._get_default_bad_words()
            self.save_word_lists()
            
        try:
            with open('data/replacements.json', 'r', encoding='utf-8') as f:
                self.replacements = json.load(f)
        except FileNotFoundError:
            self.replacements = self._get_default_replacements()
            self.save_word_lists()
    
    def _get_default_bad_words(self):
        """Get default bad words dictionary with comprehensive list"""
        return {
            "mild": [
                "damn", "darn", "crap", "hell", "piss", "suck", "stupid", "idiot", 
                "dumb", "moron", "shut up", "shutup", "wtf", "omg", "lmao", 
                "stfu", "bs", "bullshit", "pissed", "pissing", "sucks", "sucked",
                "goddamn", "goddamnit", "dammit", "freaking", "freak", "jerk"
            ],
            "moderate": [
                "fuck", "fucking", "fucked", "fucker", "fck", "fuk", "f*ck", "f**k",
                "shit", "shitty", "sht", "sh*t", "s**t", "crap", "crappy",
                "bitch", "bitches", "btch", "b*tch", "b**ch", "beach",
                "ass", "asshole", "a**", "a**hole", "arse", "arsehole",
                "dick", "d*ck", "d**k", "cock", "c*ck", "c**k", "penis",
                "pussy", "p*ssy", "p**sy", "vagina", "cunt", "c*nt", "c**t",
                "tits", "boobs", "boobies", "breast", "nipple", "nipples",
                "bastard", "b*stard", "b**tard", "slut", "sl*t", "sl**",
                "whore", "wh*re", "wh**e", "hoe", "thot", "simp", "incel",
                "horny", "sexy", "sex", "porn", "masturbate", "jerk off",
                "blow job", "blowjob", "handjob", "69", "420", "weed", "pot",
                "marijuana", "cocaine", "heroin", "meth", "drugs", "druggie"
            ],
            "severe": [
                "motherfucker", "motherf*cker", "motherf**ker", "mf", "mfer",
                "cocksucker", "c*cksucker", "c**ksucker", "cunnilingus",
                "fellatio", "orgasm", "climax", "ejaculate", "penetrate",
                "intercourse", "fornicate", "copulate", "rape", "r*pe", "r**e",
                "molest", "abuse", "assault", "violence", "kill", "murder",
                "die", "death", "suicide", "self harm", "cutting", "overdose",
                "death threat", "bomb", "terrorist", "kill yourself", "kys",
                "go die", "neck yourself", "hang yourself", "shoot yourself"
            ],
            "slurs": [
                # Racial slurs
                "nigger", "n*gger", "n**ger", "nigga", "n*gga", "n**ga",
                "negro", "n*gro", "n**ro", "coon", "c*on", "c**n",
                "spook", "darkie", "blackie", "monkey", "ape", "gorilla",
                
                # Homophobic slurs
                "faggot", "f*ggot", "f**got", "fag", "f*g", "f**",
                "queer", "qu*er", "qu**r", "homo", "h*mo", "h**o",
                "dyke", "d*ke", "d**e", "tranny", "tr*nny", "tr**ny",
                "shemale", "ladyboy", "trap",
                
                # Ableist slurs
                "retard", "ret*rd", "ret**d", "retarded", "retarted",
                "autistic", "autist", "spastic", "spaz", "mongoloid",
                "midget", "dwarf", "cripple", "gimp", "tard",
                
                # Anti-Asian slurs
                "chink", "ch*nk", "ch**k", "gook", "g*ok", "g**k",
                "jap", "nip", "slant", "oriental", "zipperhead",
                
                # Anti-Hispanic slurs
                "spic", "sp*c", "sp**", "wetback", "beaner", "greaser",
                "taco", "pablo", "jose", "juan", "border hopper",
                
                # Anti-Middle Eastern slurs
                "towelhead", "camel jockey", "terrorist", "bomber", "jihad",
                "sand nigger", "raghead", "durka", "abdul", "ahmed",
                
                # Anti-Jewish slurs
                "kike", "k*ke", "k**e", "heeb", "hymie", "sheeny", "yid",
                "jew", "jewish", "zionist", "israeli", "goldberg", "weinstein",
                
                # Anti-White slurs
                "honkey", "h*nkey", "h**key", "cracker", "cr*cker", "cr**ker",
                "redneck", "hillbilly", "whitey", "mayo", "white trash", "wigger"
            ],
            "custom": []
        }
    
    def _get_default_replacements(self):
        """Get default word replacements"""
        return {
            "fuck": "fluff", "fucking": "fluffing", "fucked": "fluffed", "fucker": "fluffer",
            "shit": "poop", "shitty": "poopy", "crap": "crud", "damn": "darn", 
            "damned": "darned", "hell": "heck", "bitch": "birch", "bitches": "birches",
            "ass": "butt", "asshole": "butthole", "dick": "richard", "cock": "rooster",
            "pussy": "kitty", "tits": "chest", "boobs": "chest", "bastard": "meanie",
            "slut": "person", "whore": "person", "stupid": "silly", "idiot": "silly person",
            "dumb": "silly", "moron": "silly person", "retard": "person", 
            "retarded": "silly", "gay": "happy", "lesbian": "person", "homo": "person",
            "fag": "person", "faggot": "person", "nigger": "[censored]", "nigga": "[censored]",
            "chink": "[censored]", "spic": "[censored]", "kike": "[censored]",
            "rape": "[inappropriate]", "kill": "defeat", "murder": "defeat", "die": "leave",
            "suicide": "[concerning content]", "wtf": "what the heck", "stfu": "be quiet",
            "bullshit": "nonsense", "motherfucker": "mean person", "cocksucker": "[censored]"
        }
    
    def save_word_lists(self):
        """Save word lists to JSON files"""
        with open('data/bad_words.json', 'w', encoding='utf-8') as f:
            json.dump(self.bad_words, f, indent=2, ensure_ascii=False)
            
        with open('data/replacements.json', 'w', encoding='utf-8') as f:
            json.dump(self.replacements, f, indent=2, ensure_ascii=False)
    
    def normalize_text(self, text: str) -> str:
        """Normalize text by removing accents and special characters"""
        # Remove accents
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
        
        # Remove zero-width characters and other unicode tricks
        text = re.sub(r'[\u200b-\u200f\u2060\ufeff\u00ad]', '', text)
        
        # Convert to lowercase
        return text.lower()
    
    def generate_variations(self, word: str) -> Set[str]:
        """Generate all possible variations of a word using leetspeak"""
        variations = {word}
        current_variations = {word}
        
        # Generate leetspeak variations
        for _ in range(3):  # Limit iterations to prevent explosion
            new_variations = set()
            for variation in current_variations:
                for char, replacements in self.leetspeak_map.items():
                    if char in variation:
                        for replacement in replacements[:3]:  # Limit replacements
                            new_var = variation.replace(char, replacement, 1)
                            new_variations.add(new_var)
            variations.update(new_variations)
            current_variations = new_variations
            
            # Prevent excessive variations
            if len(variations) > 100:
                break
        
        return variations
    
    def compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        self.patterns = {}
        
        for category, words in self.bad_words.items():
            if not words:
                continue
                
            category_patterns = []
            
            for word in words:
                # Generate variations
                variations = self.generate_variations(word.lower())
                
                for variation in variations:
                    # Create pattern that handles spacing, dots, dashes, underscores
                    pattern_chars = []
                    for char in variation:
                        if char.isalpha():
                            # Handle character substitutions
                            alternatives = self.leetspeak_map.get(char, [char])
                            char_pattern = f"[{''.join(re.escape(alt) for alt in alternatives)}]"
                            pattern_chars.append(char_pattern)
                        else:
                            pattern_chars.append(re.escape(char))
                    
                    # Join with separator pattern
                    pattern = self.separators.join(pattern_chars)
                    
                    # Word boundary handling (flexible)
                    pattern = rf'(?<![a-zA-Z]){pattern}(?![a-zA-Z])'
                    category_patterns.append(pattern)
            
            # Compile combined pattern for category
            if category_patterns:
                try:
                    combined_pattern = '|'.join(category_patterns)
                    self.patterns[category] = re.compile(combined_pattern, re.IGNORECASE | re.UNICODE)
                except re.error as e:
                    print(f"Regex compilation error for category {category}: {e}")
                    continue
    
    async def check_message(self, content: str) -> Tuple[bool, str]:
        """Check message for profanity and return censored version"""
        if not content or len(content.strip()) == 0:
            return False, content
        
        # Normalize the content
        normalized_content = self.normalize_text(content)
        original_content = content
        censored_content = content
        found_profanity = False
        
        # Store all matches to avoid overlapping replacements
        all_matches = []
        
        # Check each category
        for category, pattern in self.patterns.items():
            try:
                matches = list(pattern.finditer(normalized_content))
                for match in matches:
                    all_matches.append((match.start(), match.end(), match.group(), category))
            except Exception as e:
                print(f"Pattern matching error for category {category}: {e}")
                continue
        
        # Sort matches by position (start position)
        all_matches.sort(key=lambda x: x[0])
        
        # Apply replacements from right to left to maintain positions
        offset = 0
        for start, end, matched_word, category in reversed(all_matches):
            found_profanity = True
            
            # Find the best replacement
            replacement = self.find_replacement(matched_word, category)
            
            # Get the actual matched text from original content
            actual_start = start + offset
            actual_end = end + offset
            
            if actual_start < len(original_content) and actual_end <= len(original_content):
                original_match = original_content[actual_start:actual_end]
                
                # Preserve case
                if original_match.isupper():
                    replacement = replacement.upper()
                elif original_match.istitle():
                    replacement = replacement.title()
                elif original_match.islower():
                    replacement = replacement.lower()
                
                # Replace in content
                censored_content = (
                    censored_content[:actual_start] + 
                    replacement + 
                    censored_content[actual_end:]
                )
                
                # Update offset for position tracking
                offset += len(replacement) - (actual_end - actual_start)
        
        return found_profanity, censored_content
    
    def find_replacement(self, word: str, category: str) -> str:
        """Find appropriate replacement for a bad word"""
        word_lower = word.lower()
        
        # Remove non-alphabetic characters for lookup
        clean_word = re.sub(r'[^a-zA-Z]', '', word_lower)
        
        # Check direct replacements first
        if word_lower in self.replacements:
            return self.replacements[word_lower]
        
        if clean_word in self.replacements:
            return self.replacements[clean_word]
        
        # Check for partial matches in replacements
        for original, replacement in self.replacements.items():
            if original in clean_word or clean_word in original:
                if fuzz.ratio(clean_word, original) > 80:
                    return replacement
        
        # Category-based replacements
        category_replacements = {
            'mild': ['darn', 'fudge', 'shoot', 'heck', 'crud'],
            'moderate': ['fluff', 'sugar', 'frick', 'dang', 'beep'],
            'severe': ['[censored]', '*****', '[removed]', 'bleep'],
            'slurs': ['[inappropriate]', '[removed]', '[censored]'],
            'custom': ['***', 'beep', 'bleep']
        }
        
        if category in category_replacements:
            import random
            return random.choice(category_replacements[category])
        
        # Fallback replacements based on word length
        if len(clean_word) <= 3:
            return '***'
        elif len(clean_word) <= 5:
            return '*****'
        else:
            return '[censored]'
    
    async def add_word(self, word: str, category: str = 'custom', replacement: str = None):
        """Add a word to the filter"""
        if category not in self.bad_words:
            self.bad_words[category] = []
        
        word_lower = word.lower()
        if word_lower not in [w.lower() for w in self.bad_words[category]]:
            self.bad_words[category].append(word_lower)
        
        if replacement:
            self.replacements[word_lower] = replacement
        
        self.save_word_lists()
        self.compile_patterns()
    
    async def remove_word(self, word: str) -> bool:
        """Remove a word from the filter"""
        removed = False
        word_lower = word.lower()
        
        for category, words in self.bad_words.items():
            original_length = len(words)
            self.bad_words[category] = [w for w in words if w.lower() != word_lower]
            if len(self.bad_words[category]) < original_length:
                removed = True
        
        if word_lower in self.replacements:
            del self.replacements[word_lower]
            removed = True
        
        if removed:
            self.save_word_lists()
            self.compile_patterns()
        
        return removed
    
    async def is_on_cooldown(self, user_id: int) -> bool:
        """Check if user is on cooldown"""
        if user_id not in self.cooldowns:
            return False
        
        return time.time() - self.cooldowns[user_id] < 2  # 2 second cooldown
    
    async def add_cooldown(self, user_id: int):
        """Add user to cooldown"""
        self.cooldowns[user_id] = time.time()
        
        # Clean old cooldowns periodically
        current_time = time.time()
        expired_users = [uid for uid, timestamp in self.cooldowns.items() 
                        if current_time - timestamp > 60]  # Remove after 1 minute
        for uid in expired_users:
            del self.cooldowns[uid]
    
    def get_word_count(self) -> Dict[str, int]:
        """Get count of words per category"""
        return {category: len(words) for category, words in self.bad_words.items()}
    
    def get_total_words(self) -> int:
        """Get total number of filtered words"""
        return sum(len(words) for words in self.bad_words.values())
