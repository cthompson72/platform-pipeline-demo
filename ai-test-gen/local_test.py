"""
Local test harness for the AI test generation module.
Feeds a sample diff to the generator and prints the results.
Does not require GitHub API access — outputs to console instead of posting a PR comment.
"""
import os
import sys
import json

# Add parent directory to path so we can import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generator import generate_tests
from formatter import format_pr_comment

SAMPLE_DIFF = """
diff --git a/src/main/java/com/demo/pipeline/controller/ProductController.java b/src/main/java/com/demo/pipeline/controller/ProductController.java
index abc1234..def5678 100644
--- a/src/main/java/com/demo/pipeline/controller/ProductController.java
+++ b/src/main/java/com/demo/pipeline/controller/ProductController.java
@@ -45,6 +45,24 @@ public class ProductController {
         return ResponseEntity.ok(products);
     }

+    @GetMapping("/api/products/featured")
+    public ResponseEntity<List<Product>> getFeaturedProducts(
+            @RequestParam(defaultValue = "5") int limit) {
+        List<Product> featured = productRepository.findByInStockTrue()
+            .stream()
+            .sorted((a, b) -> b.getCreatedAt().compareTo(a.getCreatedAt()))
+            .limit(limit)
+            .collect(Collectors.toList());
+        return ResponseEntity.ok(featured);
+    }
+
+    @DeleteMapping("/api/products/{id}")
+    public ResponseEntity<Void> deleteProduct(@PathVariable Long id) {
+        productRepository.deleteById(id);
+        return ResponseEntity.noContent().build();
+    }
+
+    @PutMapping("/api/products/{id}")
+    public ResponseEntity<Product> updateProduct(
+            @PathVariable Long id,
+            @Valid @RequestBody Product product) {
+        return productRepository.findById(id)
+            .map(existing -> {
+                existing.setName(product.getName());
+                existing.setPrice(product.getPrice());
+                existing.setCategory(product.getCategory());
+                return ResponseEntity.ok(productRepository.save(existing));
+            })
+            .orElse(ResponseEntity.notFound().build());
+    }
"""

def main():
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        print("Set it with: export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    print("=" * 60)
    print("AI Test Generation — Local Test")
    print("=" * 60)
    print()

    changed_files = ["src/main/java/com/demo/pipeline/controller/ProductController.java"]

    print(f"Analyzing diff for: {', '.join(changed_files)}")
    print(f"Experience ID: PPD-LOCAL-TEST")
    print()
    print("Calling Claude API...")
    print()

    result = generate_tests(
        diff_text=SAMPLE_DIFF,
        changed_files=changed_files,
        experience_id="PPD-LOCAL-TEST",
        pr_number=0,  # No real PR for local testing
    )

    # Print the formatted PR comment
    comment = format_pr_comment(result)
    print(comment)
    print()

    # Also write the JSON results for the quality gate
    os.makedirs("ai-test-gen/results", exist_ok=True)
    results_file = "ai-test-gen/results/test-gen-results.json"
    with open(results_file, "w") as f:
        json.dump({
            "experience_id": result.experience_id,
            "pr_number": result.pr_number,
            "total_suggestions": len(result.suggested_tests),
            "high_priority": sum(1 for t in result.suggested_tests if t.priority == "high"),
            "medium_priority": sum(1 for t in result.suggested_tests if t.priority == "medium"),
            "low_priority": sum(1 for t in result.suggested_tests if t.priority == "low"),
        }, f, indent=2)

    print(f"Results written to {results_file}")
    print()

    # Print summary
    print("=" * 60)
    print(f"Summary: {result.summary}")
    print("=" * 60)

if __name__ == "__main__":
    main()
