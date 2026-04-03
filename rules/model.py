import torch
from transformers import AutoProcessor, AutoModelForCausalLM, AutoModel
import kagglehub
from PIL import Image
import logging

logger = logging.getLogger("Guardian Cam Service Model")

class GuardianCamRulesModel:
    def __init__(self, model_name):
        self.model = None
        self.processor = None
        self.model_name = model_name

    def init(self):
        model_path = kagglehub.model_download(f"google/gemma-4/transformers/{self.model_name}")
        logger.info(f"Model downloaded to {model_path}")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            dtype=torch.bfloat16,
            device_map="auto"
        )
        self.processor = AutoProcessor.from_pretrained(model_path)

        warm_up_message = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        text = self.processor.apply_chat_template(
            warm_up_message,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )
        logger.info("Warming up model...")
        inputs = self.processor(text=text, return_tensors="pt").to(self.model.device)
        self.model.generate(**inputs, max_new_tokens=1024)
        logger.info("Warm up complete")

    def evaluate_rule(self, rule: str, image: Image.Image):
        # Example
        # User enters: Notify me if: a cat is eating.
        # Rule: a cat is eating.
        logger.debug(f"Evaluating is {rule}?")
        rule_message = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "system", "content": "Answer questions with yes or no"},
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": f"is {rule}?"},
                ],
            }
        ]

        rule_text = self.processor.apply_chat_template(
            rule_message,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )
        inputs = self.processor(text=rule_text, images=image, return_tensors="pt").to(self.model.device)
        input_len = inputs["input_ids"].shape[-1]
        outputs = self.model.generate(**inputs, max_new_tokens=1024)
        response = self.processor.decode(outputs[0][input_len:], skip_special_tokens=False)
        response = self.processor.parse_response(response)['content'].lower()
        logger.debug(f'Response: {response}')
        return response == 'yes'




