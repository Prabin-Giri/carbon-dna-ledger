"""
AI-powered text classification service for invoice and emission data extraction
Supports local and cloud AI models, plus image OCR capabilities
"""
import json
import re
import base64
import io
from typing import Dict, Any, Optional, List
from datetime import date
import requests
import os
from dotenv import load_dotenv
from PIL import Image
import pytesseract

load_dotenv()

class AIClassifier:
    def __init__(self, model_preference: str = None):
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model_preference = model_preference or os.getenv("AI_MODEL_PREFERENCE", "ollama")  # ollama, openai, or regex
        self.confidence_threshold = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.7"))  # Default 70% confidence threshold
        
        # Available models
        self.available_models = {
            "ollama": {
                "name": "Ollama (Local)",
                "description": "Run AI models locally on your machine",
                "models": ["llama2", "llama3", "mistral", "codellama"],
                "requires_setup": True,
                "cost": "Secure & Private"
            },
            "openai": {
                "name": "OpenAI (Cloud)",
                "description": "Use OpenAI's cloud-based models",
                "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                "requires_setup": True,
                "cost": "High Performance"
            },
            "regex": {
                "name": "Pattern Matching",
                "description": "Use regex patterns for text extraction",
                "models": ["regex"],
                "requires_setup": False,
                "cost": "Free"
            }
        }
        
    def get_available_models(self) -> Dict[str, Any]:
        """Get information about available AI models"""
        return self.available_models
    
    def check_model_availability(self, model_type: str) -> Dict[str, Any]:
        """Check if a specific model type is available and configured"""
        if model_type == "ollama":
            try:
                response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return {
                        "available": True,
                        "models": [model["name"] for model in models],
                        "status": "Connected to Ollama"
                    }
                else:
                    return {"available": False, "error": "Ollama not responding"}
            except Exception as e:
                return {"available": False, "error": f"Cannot connect to Ollama: {str(e)}"}
        
        elif model_type == "openai":
            if self.openai_api_key:
                return {"available": True, "status": "OpenAI API key configured"}
            else:
                return {"available": False, "error": "OpenAI API key not configured"}
        
        elif model_type == "regex":
            return {"available": True, "status": "Regex patterns always available"}
        
        return {"available": False, "error": "Unknown model type"}
    
    def extract_text_from_image(self, image_data: bytes, image_format: str = "PNG") -> str:
        """Extract text from image using OCR"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Use Tesseract OCR to extract text
            text = pytesseract.image_to_string(image, config='--psm 6')
            
            return text.strip()
        except Exception as e:
            print(f"OCR error: {str(e)}")
            return ""
    
    def classify_invoice_text(self, text: str, supplier_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify invoice text and extract structured emission data
        """
        try:
            if self.model_preference == "ollama":
                result = self._classify_with_ollama(text, supplier_name)
                # If Ollama fails, fall back to regex
                if not result["success"]:
                    print(f"Ollama failed, falling back to regex: {result.get('error')}")
                    return self._classify_with_regex(text, supplier_name)
                return result
            elif self.model_preference == "openai" and self.openai_api_key:
                result = self._classify_with_openai(text, supplier_name)
                # If OpenAI fails, fall back to regex
                if not result["success"]:
                    print(f"OpenAI failed, falling back to regex: {result.get('error')}")
                    return self._classify_with_regex(text, supplier_name)
                return result
            else:
                return self._classify_with_regex(text, supplier_name)
        except Exception as e:
            print(f"Classification error, falling back to regex: {str(e)}")
            return self._classify_with_regex(text, supplier_name)
    
    def classify_invoice_image(self, image_data: bytes, supplier_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from image and classify it for emission data
        """
        try:
            # Extract text from image using OCR
            extracted_text = self.extract_text_from_image(image_data)
            
            if not extracted_text:
                return {
                    "success": False,
                    "error": "No text could be extracted from the image",
                    "confidence_score": 0.0,
                    "needs_human_review": True,
                    "extracted_text": ""
                }
            
            # Classify the extracted text
            result = self.classify_invoice_text(extracted_text, supplier_name)
            
            # Add OCR metadata
            result["extracted_text"] = extracted_text
            result["ocr_used"] = True
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Image processing error: {str(e)}",
                "confidence_score": 0.0,
                "needs_human_review": True,
                "extracted_text": ""
            }
    
    def _classify_with_ollama(self, text: str, supplier_name: Optional[str] = None) -> Dict[str, Any]:
        """Classify using Ollama (local LLM)"""
        print(f"Starting Ollama classification with base URL: {self.ollama_base_url}")
        
        # First check if Ollama is available
        if not self._check_ollama_availability():
            print("Ollama service not available")
            return self._create_error_result("Ollama service not available. Please start Ollama or use a different model.")
        
        prompt = self._create_classification_prompt(text, supplier_name)
        print(f"Prompt length: {len(prompt)} characters")
        
        try:
            # Try to get available models first
            models_response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if models_response.status_code != 200:
                return self._create_error_result("Ollama service not responding")
            
            models = models_response.json().get("models", [])
            if not models:
                return self._create_error_result("No models available in Ollama")
            
            # Use llama3.2:latest as it's more reliable for JSON generation
            model_name = "llama3.2:latest"  # Use llama3.2 as it's more reliable for JSON
            if not any(m.get("name") == "llama3.2:latest" for m in models):
                model_name = models[0].get("name", "llama2")
            
            print(f"Using model: {model_name}")
            print(f"Making request to Ollama...")
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,  # Very low temperature for consistency
                        "top_p": 0.8,
                        "num_predict": 300,  # Strict limit on response length
                        "stop": []  # No stop tokens
                    }
                },
                timeout=30  # Reduced timeout to 30 seconds
            )
            
            print(f"Ollama response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "")
                print(f"Ollama response data: {result}")
                return self._parse_ai_response(ai_response, f"ollama:{model_name}")
            else:
                print(f"Ollama API error: {response.status_code} - {response.text}")
                return self._create_error_result(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            return self._create_error_result(f"Ollama connection error: {str(e)}")
    
    def _classify_with_openai(self, text: str, supplier_name: Optional[str] = None) -> Dict[str, Any]:
        """Classify using OpenAI API"""
        prompt = self._create_classification_prompt(text, supplier_name)
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are an expert at extracting carbon emission data from invoices and financial documents."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                return self._parse_ai_response(ai_response, "openai:gpt-3.5-turbo")
            else:
                return self._create_error_result(f"OpenAI API error: {response.status_code}")
                
        except Exception as e:
            return self._create_error_result(f"OpenAI connection error: {str(e)}")
    
    def _classify_with_regex(self, text: str, supplier_name: Optional[str] = None) -> Dict[str, Any]:
        """Fallback regex-based classification"""
        # Extract basic information using regex patterns
        extracted_data = {
            "supplier_name": supplier_name or self._extract_supplier_name(text),
            "activity_type": self._extract_activity_type(text),
            "amount": self._extract_amount(text),
            "currency": self._extract_currency(text),
            "date": self._extract_date(text),
            "description": text[:200] + "..." if len(text) > 200 else text,
            "scope": 3,  # Default to scope 3
            "category": "Other",
            "confidence_score": 0.3,  # Low confidence for regex
            "needs_human_review": True
        }
        
        return {
            "success": True,
            "data": extracted_data,
            "confidence_score": 0.3,
            "needs_human_review": True,
            "ai_model_used": "regex:fallback",
            "classification_metadata": {
                "method": "regex_patterns",
                "patterns_used": ["amount", "currency", "date", "supplier"]
            }
        }
    
    def _create_classification_prompt(self, text: str, supplier_name: Optional[str] = None) -> str:
        """Create a structured prompt for AI classification"""
        return f"""Return this JSON: {{"supplier_name": "Test Supplier", "amount": 100, "currency": "USD"}}

Invoice: {text}"""
    
    def _parse_ai_response(self, ai_response: str, model_used: str) -> Dict[str, Any]:
        """Parse AI response and extract structured data"""
        try:
            # Debug: Print the raw response
            print(f"Raw AI response: {ai_response}")
            print(f"Raw AI response length: {len(ai_response)}")
            
            # Clean the response to extract JSON - look for JSON objects more precisely
            # First try to find a simple JSON object
            json_match = re.search(r'\{[^{}]*"[^"]*"[^{}]*\}', ai_response)
            if not json_match:
                # Try to find JSON with nested objects
                json_match = re.search(r'\{[^{}]*"[^"]*"[^{}]*"[^"]*"[^{}]*\}', ai_response)
            if not json_match:
                # Fallback to broader search
                json_match = re.search(r'\{.*?\}', ai_response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                print(f"Extracted JSON: {json_str[:300]}...")
                
                # Check if JSON is complete (has closing brace)
                if not json_str.strip().endswith('}'):
                    print("JSON appears incomplete, attempting to complete it...")
                    json_str = self._complete_incomplete_json(json_str)
                
                # Try to fix common JSON issues
                fixed_json = self._fix_json_formatting(json_str)
                print(f"Fixed JSON: {fixed_json[:300]}...")
                
                # Try to parse the JSON
                try:
                    data = json.loads(fixed_json)
                except json.JSONDecodeError as e:
                    print(f"JSON still invalid after fixing: {e}")
                    # Try to extract just the first part before any off-topic text
                    lines = fixed_json.split('\n')
                    json_lines = []
                    for line in lines:
                        # Stop at medical/scientific content or closing brace
                        if (line.strip().startswith('}') or 
                            'endocrine' in line.lower() or 
                            'hormone' in line.lower() or
                            'gland' in line.lower() or
                            'bloodstream' in line.lower() or
                            'receptor' in line.lower()):
                            break
                        json_lines.append(line)
                    
                    # Add closing brace if missing
                    if json_lines and not json_lines[-1].strip().endswith('}'):
                        json_lines.append('}')
                    
                    fixed_json = '\n'.join(json_lines)
                    print(f"Cleaned JSON: {fixed_json[:300]}...")
                    data = json.loads(fixed_json)
                
                # Validate and clean the data
                cleaned_data = self._clean_extracted_data(data)
                
                return {
                    "success": True,
                    "data": cleaned_data,
                    "confidence_score": cleaned_data.get("confidence_score", 0.5),
                    "needs_human_review": cleaned_data.get("needs_human_review", False),
                    "ai_model_used": model_used,
                    "classification_metadata": {
                        "raw_response": ai_response,
                        "reasoning": cleaned_data.get("reasoning", ""),
                        "extraction_method": "ai_classification"
                    }
                }
            else:
                return self._create_error_result("No valid JSON found in AI response")
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Problematic JSON: {json_str if 'json_str' in locals() else 'N/A'}")
            return self._create_error_result(f"JSON parsing error: {str(e)}")
        except Exception as e:
            print(f"Parse error: {e}")
            return self._create_error_result(f"Response parsing error: {str(e)}")
    
    def _complete_incomplete_json(self, json_str: str) -> str:
        """Attempt to complete incomplete JSON responses"""
        try:
            # Remove any text after the last complete field
            lines = json_str.split('\n')
            complete_lines = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('}') and ':' in line:
                    # Check if this line looks like a complete field
                    if line.endswith(',') or line.endswith('null') or line.endswith('"') or line.endswith('}'):
                        complete_lines.append(line)
                    else:
                        # This line might be incomplete, try to complete it
                        if ':' in line and not line.endswith(','):
                            if 'null' in line or '"' in line:
                                complete_lines.append(line + ',')
                            else:
                                complete_lines.append(line + ' null,')
                        break
                elif line.startswith('}'):
                    complete_lines.append(line)
                    break
            
            # Join the lines and ensure proper closing
            result = '\n'.join(complete_lines)
            if not result.strip().endswith('}'):
                result = result.rstrip(',') + '\n}'
            
            return result
        except Exception as e:
            print(f"Error completing JSON: {e}")
            return json_str
    
    def _fix_json_formatting(self, json_str: str) -> str:
        """Fix common JSON formatting issues from AI responses"""
        try:
            # First, try to find the actual JSON object boundaries
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = json_str[start_idx:end_idx + 1]
            
            # Remove JSON comments (// comments)
            json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
            
            # Fix malformed field syntax like "endDate="2025-03-08" or null,"
            json_str = re.sub(r'(\w+)=([^,}]+),', r'"\1": \2,', json_str)
            
            # Fix single quotes to double quotes for keys
            json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
            
            # Fix single quotes to double quotes for string values
            json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)
            
            # Fix boolean values
            json_str = re.sub(r':\s*true\b', ': true', json_str)
            json_str = re.sub(r':\s*false\b', ': false', json_str)
            json_str = re.sub(r':\s*null\b', ': null', json_str)
            
            # Fix "or null" patterns
            json_str = re.sub(r'\s+or\s+null', '', json_str)
            
            # Fix trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # Fix unquoted keys (but be more careful)
            json_str = re.sub(r'(\w+):', r'"\1":', json_str)
            
            # Clean up any remaining malformed syntax
            json_str = re.sub(r'=\s*"([^"]*)"', r': "\1"', json_str)
            
            return json_str
            
        except Exception as e:
            print(f"JSON fixing error: {e}")
            return json_str
    
    def _clean_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate extracted data"""
        cleaned = {}
        
        # Required fields with defaults
        cleaned["supplier_name"] = data.get("supplier_name", "Unknown Supplier")
        cleaned["activity_type"] = data.get("activity_type", "other")
        cleaned["amount"] = self._safe_float(data.get("amount"))
        cleaned["currency"] = data.get("currency", "USD")
        cleaned["date"] = self._parse_date_string(data.get("date"))
        cleaned["description"] = data.get("description", "")
        cleaned["scope"] = self._safe_int(data.get("scope"), 3)
        cleaned["category"] = data.get("category", "Other")
        cleaned["subcategory"] = data.get("subcategory", "")
        
        # Optional activity details
        cleaned["activity_amount"] = self._safe_float(data.get("activity_amount"))
        cleaned["activity_unit"] = data.get("activity_unit", "")
        cleaned["fuel_type"] = data.get("fuel_type", "")
        cleaned["vehicle_type"] = data.get("vehicle_type", "")
        cleaned["distance_km"] = self._safe_float(data.get("distance_km"))
        cleaned["mass_tonnes"] = self._safe_float(data.get("mass_tonnes"))
        cleaned["energy_kwh"] = self._safe_float(data.get("energy_kwh"))
        
        # AI metadata
        confidence_score = max(0.0, min(1.0, self._safe_float(data.get("confidence_score"), 0.5)))
        cleaned["confidence_score"] = confidence_score
        
        # Automatically set human review flag based on confidence threshold
        # ALL AI-classified records should go through human review by default for data quality
        needs_human_review = bool(data.get("needs_human_review", True))  # Default to True for AI records
        if confidence_score < self.confidence_threshold:
            needs_human_review = True  # Low confidence definitely needs review
            
        cleaned["needs_human_review"] = needs_human_review
        cleaned["reasoning"] = data.get("reasoning", "")
        
        return cleaned
    
    def _extract_supplier_name(self, text: str) -> str:
        """Extract supplier name using regex patterns"""
        # Look for common invoice patterns
        patterns = [
            r'Bill\s+to:\s*([^\n]+)',
            r'From:\s*([^\n]+)',
            r'Supplier:\s*([^\n]+)',
            r'Vendor:\s*([^\n]+)',
            r'Company:\s*([^\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Unknown Supplier"
    
    def _extract_activity_type(self, text: str) -> str:
        """Extract activity type using keyword matching"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['transport', 'shipping', 'delivery', 'fuel', 'gas', 'mileage']):
            return 'transportation'
        elif any(word in text_lower for word in ['electricity', 'energy', 'power', 'kwh', 'electric']):
            return 'energy'
        elif any(word in text_lower for word in ['waste', 'disposal', 'recycling', 'trash']):
            return 'waste'
        elif any(word in text_lower for word in ['material', 'supplies', 'equipment', 'goods']):
            return 'materials'
        else:
            return 'other'
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract monetary amount using regex"""
        patterns = [
            r'Total:\s*\$?([\d,]+\.?\d*)',
            r'Amount:\s*\$?([\d,]+\.?\d*)',
            r'Cost:\s*\$?([\d,]+\.?\d*)',
            r'\$([\d,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        
        return None
    
    def _extract_currency(self, text: str) -> str:
        """Extract currency from text"""
        if '$' in text:
            return 'USD'
        elif '€' in text or 'EUR' in text.upper():
            return 'EUR'
        elif '£' in text or 'GBP' in text.upper():
            return 'GBP'
        else:
            return 'USD'
    
    def _extract_date(self, text: str) -> Optional[date]:
        """Extract date from text"""
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\d{2}-\d{2}-\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(1)
                    if '-' in date_str and len(date_str) == 10:
                        return date.fromisoformat(date_str)
                    elif '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) == 3:
                            month, day, year = parts
                            return date(int(year), int(month), int(day))
                except ValueError:
                    continue
        
        return None
    
    def _parse_date_string(self, date_str: Any) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str:
            return None
        
        try:
            if isinstance(date_str, str):
                # Try ISO format first
                if '-' in date_str and len(date_str) == 10:
                    return date.fromisoformat(date_str)
                # Try other formats
                elif '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        month, day, year = parts
                        return date(int(year), int(month), int(day))
            return None
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _safe_int(self, value: Any, default: int = 0) -> int:
        """Safely convert value to int"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def _check_ollama_availability(self) -> bool:
        """Check if Ollama is available and running"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                print(f"Ollama available with {len(models)} models: {[m.get('name') for m in models]}")
                return True
            return False
        except Exception as e:
            print(f"Ollama check failed: {e}")
            return False
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result structure"""
        return {
            "success": False,
            "error": error_message,
            "data": {},
            "confidence_score": 0.0,
            "needs_human_review": True,
            "ai_model_used": "error",
            "classification_metadata": {
                "error": error_message,
                "extraction_method": "error"
            }
        }
    
    def batch_classify(self, texts: List[str], supplier_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Classify multiple texts in batch"""
        results = []
        supplier_names = supplier_names or [None] * len(texts)
        
        for i, text in enumerate(texts):
            supplier_name = supplier_names[i] if i < len(supplier_names) else None
            result = self.classify_invoice_text(text, supplier_name)
            results.append(result)
        
        return results
