import shelve
from datetime import datetime

class TranslationCache:
    def __init__(self):
        self.store = shelve.open("translations.db")
    
    def get(self, key: str):
        return self.store.get(key)
    
    def set(self, key: str, value: str):
        self.store[key] = {
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
    
    def clear(self):
        self.store.clear()
    
    def __del__(self):
        self.store.close()
