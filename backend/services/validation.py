class ValidationService:
    def validate_output(self, response_data: dict) -> dict:
        """
        Validates the generated response before sending to frontend.
        This acts as a final guardrail.
        """
        
        # Example validation: Check for sensitive data leakage
        if "password" in str(response_data).lower():
            return {
                "valid": False, 
                "error": "Sensitive data detected.", 
                "safe_response": "I cannot display that information for security reasons."
            }
        
        # Example validation: Ensure transaction requests have explicit approval status
        if response_data.get("type") == "transaction":
            if response_data.get("data", {}).get("status") != "pending_approval":
                # In a real app, this might flag an error or force it to pending
                pass

        return {"valid": True}
