from llama_cpp import Llama
import base64, json

llm = Llama(
    model_path=r"E:\ai models\Qwen3-VL-2B\Qwen3-VL-2B-Instruct-UD-Q4_K_XL 2.gguf",
    mmproj=r"E:\ai models\Qwen3-VL-2B\mmproj-F16 2.gguf",
    n_ctx=2048,
    n_threads=4,
    n_gpu_layers=0,
    verbose=False
)
# ← غير المسار لأي صورة عندك
IMAGE_PATH = r"G:\Designs\For Clothes\Screenshot 2025-08-01 000421.png"

with open(IMAGE_PATH, "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

response = llm.create_chat_completion(
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
            {"type": "text",
             "text": """Analyze this image for silk screen printing.
Return ONLY valid JSON, no explanation:
{
  "image_class": "text_logo" or "artwork" or "photo",
  "num_colors": 1-8,
  "use_halftone": true or false,
  "smoothing_factor": 0.1-0.5
}"""}
        ]
    }],
    temperature=0.1,
    max_tokens=200
)

raw = response["choices"][0]["message"]["content"]
clean = raw.strip().strip("```json").strip("```").strip()

try:
    result = json.loads(clean)
    print("✅ النتيجة:")
    print(json.dumps(result, indent=2))
except:
    print("Raw output:", raw)