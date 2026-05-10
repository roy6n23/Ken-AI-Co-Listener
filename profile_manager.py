"""Profile management system with category-based organization."""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

PROFILES_DIR = Path(__file__).parent / "user_profiles"
PROFILES_DIR.mkdir(exist_ok=True)

PROFILE_CATEGORIES = {
    "career": {
        "label": "💼 Career & Employment",
        "fields": ["current_role", "industry", "years_experience", "goals", "concerns"]
    },
    "immigration": {
        "label": "🛂 Immigration Status",
        "fields": ["visa_type", "priority_date", "current_status", "timeline", "concerns"]
    },
    "marriage": {
        "label": "💍 Marriage & Family",
        "fields": ["marital_status", "spouse_status", "dependents", "concerns"]
    },
    "financial": {
        "label": "💰 Financial Situation",
        "fields": ["income_level", "assets", "tax_status", "concerns"]
    },
    "education": {
        "label": "🎓 Education Background",
        "fields": ["degree", "institution", "field", "year", "concerns"]
    }
}


class ProfileManager:
    def __init__(self):
        self.profiles_dir = PROFILES_DIR

    def list_profiles(self) -> List[Dict]:
        """List all saved profiles with metadata."""
        profiles = []
        for file in self.profiles_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    profiles.append({
                        "id": file.stem,
                        "name": data.get("name", file.stem),
                        "created": data.get("created", ""),
                        "last_used": data.get("last_used", ""),
                        "categories": list(data.get("categories", {}).keys())
                    })
            except Exception as e:
                print(f"Error loading profile {file}: {e}")
        return sorted(profiles, key=lambda x: x.get("last_used", ""), reverse=True)

    def load_profile(self, profile_id: str) -> Optional[Dict]:
        """Load a profile by ID."""
        file_path = self.profiles_dir / f"{profile_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, 'r') as f:
                profile = json.load(f)
                profile["last_used"] = datetime.now().isoformat()
                self.save_profile(profile_id, profile)
                return profile
        except Exception as e:
            print(f"Error loading profile: {e}")
            return None

    def save_profile(self, profile_id: str, profile_data: Dict) -> bool:
        """Save or update a profile."""
        file_path = self.profiles_dir / f"{profile_id}.json"
        try:
            if not profile_data.get("created"):
                profile_data["created"] = datetime.now().isoformat()
            profile_data["last_used"] = datetime.now().isoformat()

            with open(file_path, 'w') as f:
                json.dump(profile_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile."""
        file_path = self.profiles_dir / f"{profile_id}.json"
        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting profile: {e}")
            return False

    def create_profile_from_categories(self, name: str, categories: Dict) -> str:
        """Create a new profile from category data."""
        profile_id = name.lower().replace(" ", "_")
        profile_data = {
            "name": name,
            "categories": categories,
            "created": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        }
        self.save_profile(profile_id, profile_data)
        return profile_id

    def profile_to_pipeline_format(self, profile_data: Dict) -> Dict:
        """Convert categorized profile to pipeline format."""
        categories = profile_data.get("categories", {})

        # Build situation text from all categories
        situation_parts = []
        concerns = []

        for cat_name, cat_data in categories.items():
            if not cat_data:
                continue
            cat_label = PROFILE_CATEGORIES.get(cat_name, {}).get("label", cat_name)
            parts = [f"{k}: {v}" for k, v in cat_data.items() if v and k != "concerns"]
            if parts:
                situation_parts.append(f"{cat_label} — {', '.join(parts)}")
            if cat_data.get("concerns"):
                concerns.append(cat_data["concerns"])

        return {
            "name": profile_data.get("name", "User"),
            "situation": " | ".join(situation_parts),
            "concerns": concerns,
            "knowledge_level": self._infer_knowledge_level(profile_data)
        }

    def _infer_knowledge_level(self, profile_data: Dict) -> str:
        """Infer knowledge level from profile completeness."""
        categories = profile_data.get("categories", {})
        total_fields = sum(len(cat) for cat in categories.values())

        if total_fields >= 10:
            return "advanced"
        elif total_fields >= 5:
            return "intermediate"
        else:
            return "beginner"


def get_profile_choices() -> List[tuple]:
    """Get profile choices for Gradio dropdown."""
    manager = ProfileManager()
    profiles = manager.list_profiles()
    choices = [("➕ Create New Profile", "new")]
    for p in profiles:
        label = f"{p['name']} ({', '.join(p['categories'])})"
        choices.append((label, p['id']))
    return choices
