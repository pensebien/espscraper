import json

class EmailNotification:
    def __init__(self, jsonl_path, output_path="product_summary.txt"):
        self.jsonl_path = jsonl_path
        self.output_path = output_path

    def generate_summary(self, limit=10):
        try:
            products = []
            with open(self.jsonl_path) as f:
                for line in f:
                    if line.strip():
                        products.append(json.loads(line))
                        if len(products) >= limit:
                            break
            with open(self.output_path, "w") as out:
                for p in products:
                    out.write(f"📦 {p.get('ProductID', 'N/A')} | 🏷️ {p.get('Name', 'N/A')} | 🌐   {p.get('URL', 'N/A')}\n")
        except Exception:
            with open(self.output_path, "w") as out:
                out.write("No products found or error reading file.")

if __name__ == "__main__":
    notifier = EmailNotification("espscraper/data/final_product_details.jsonl")
    notifier.generate_summary()