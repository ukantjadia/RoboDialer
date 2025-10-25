import os
import logging
from config.config import Config

logger = logging.getLogger(__name__)

class PromptController:
    """
    Handles prompt template path resolution and prompt building.
    """
    @classmethod
    def get_prompt_path(cls, tone, focus):
        """
        Returns the file path of the prompt based on tone and focus.
        Example: tone='friendly', focus='sales' → prompt_bank/friendly_sales_v1.txt
        """
        filename = f"{tone.lower()}_{focus.lower()}_{Config.PROMPT_TEMPLATE_VERSION}.txt"
        return os.path.join(Config.PROMPT_DIR, filename)

    @classmethod
    def build_prompt(cls, tone, focus, company_name, industry, context):
        """
        Loads the template file and replaces placeholders with real values.
        Raises FileNotFoundError if the template is missing, or Exception on other errors.
        """
        prompt_path = cls.get_prompt_path(tone, focus)

        if not os.path.exists(prompt_path):
            logger.warning(f"Prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt template not found for: {tone} + {focus}")

        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()

            prompt = (
                template.replace("{{company_name}}", company_name)
                        .replace("{{context}}", context)
                        .replace("{{industry}}", industry)
            )

            logger.info(f"Prompt generated successfully for {tone}_{focus}")
            return prompt

        except Exception as e:
            logger.error("Error while building prompt", exc_info=True)
            raise Exception("Error generating the prompt.")

    @staticmethod
    def build_system_prompt(system_prompt_file, template_content, company_name, person_name, industry, tone, context_point):
        """
        Loads the system prompt file and injects the user template and personalization fields.
        - system_prompt_file: path to the prompt file (e.g., casual_sales_v1.txt)
        - template_content: the user's template (with {{context}}, etc. already filled)
        - company_name, person_name, industry, tone: personalization fields
        - context_point: the current context snippet
        Returns the final prompt string for the LLM.
        """
        if not os.path.exists(system_prompt_file):
            logger.warning(f"Prompt file not found: {system_prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {system_prompt_file}")
        try:
            with open(system_prompt_file, "r", encoding="utf-8") as f:
                system_prompt = f.read()
            # Replace placeholders in the system prompt
            prompt = (
                system_prompt
                .replace("{{company_name}}", company_name)
                .replace("{{person_name}}", person_name)
                .replace("{{industry}}", industry)
                .replace("{{tone}}", tone)
                .replace("{{template_content}}", template_content)
                .replace("{{context}}", context_point)
            )
            logger.info(f"System prompt generated successfully from {system_prompt_file}")
            return prompt
        except Exception as e:
            logger.error("Error while building system prompt", exc_info=True)
            raise Exception("Error generating the system prompt.")

    @staticmethod
    def build_context_rewrite_prompt(tone, template_content, company_name, person_name, industry, context_point):
        """
        Builds a prompt for rewriting a single context point to fit a template and tone.
        This is the new v2 approach where LLM only rewrites the context point.

        Args:
            tone: The selected tone (friendly, casual, etc.)
            template_content: The user's template with placeholders
            company_name, person_name, industry: Personalization fields
            context_point: The context point to be rewritten

        Returns:
            The complete prompt string for the LLM
        """
        from config.config import Config

        # Build the prompt file path for v2
        prompt_filename = f"{tone.lower()}_{Config.PROMPT_TEMPLATE_VERSION_V2}.txt"
        prompt_path = os.path.join(Config.PROMPT_DIR_V2, prompt_filename)

        if not os.path.exists(prompt_path):
            logger.warning(f"Prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt file not found for tone: {tone}")

        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()

            # Replace placeholders in the system prompt
            prompt = (
                system_prompt
                .replace("{{company_name}}", company_name)
                .replace("{{person_name}}", person_name)
                .replace("{{industry}}", industry)
                .replace("{{template_content}}", template_content)
                .replace("{{context}}", context_point)
            )

            logger.info(f"Context rewrite prompt generated successfully for tone: {tone}")
            return prompt

        except Exception as e:
            logger.error("Error while building context rewrite prompt", exc_info=True)
            raise Exception("Error generating the context rewrite prompt.")