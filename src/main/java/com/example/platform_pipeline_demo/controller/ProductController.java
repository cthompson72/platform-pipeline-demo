package com.example.platform_pipeline_demo.controller;

import com.example.platform_pipeline_demo.model.Product;
import com.example.platform_pipeline_demo.repository.ProductRepository;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.lang.management.ManagementFactory;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    @Autowired
    private ProductRepository productRepository;

    // ── VULNERABILITY 1: Hardcoded credential ────────────────────────
    // Semgrep + Gitleaks should flag this
    private static final String API_SECRET = "sk_live_beautytech_2025_prod";

    // ── Clean endpoint — standard Spring Data ────────────────────────
    @GetMapping
    public List<Product> getAllProducts() {
        return productRepository.findAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Product> getProduct(@PathVariable Long id) {
        return productRepository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    // ── Clean endpoint — safe parameterized query ────────────────────
    @GetMapping("/search-safe")
    public List<Product> searchSafe(@RequestParam String q) {
        return productRepository.findByNameContainingIgnoreCase(q);
    }

    @GetMapping("/search")
    public List<Product> searchProducts(@RequestParam String q) {
        return productRepository.findByNameContainingIgnoreCase(q);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Product createProduct(@Valid @RequestBody Product product) {
        return productRepository.save(product);
    }

    // ── Detailed health check ────────────────────────────────────────
    @GetMapping("/health/detailed")
    public Map<String, Object> detailedHealth() {
        Runtime runtime = Runtime.getRuntime();
        long uptimeMillis = ManagementFactory.getRuntimeMXBean().getUptime();
        Duration uptime = Duration.ofMillis(uptimeMillis);

        Map<String, Object> health = new LinkedHashMap<>();
        health.put("status", "UP");
        health.put("database", "H2 (in-memory)");
        health.put("productCount", productRepository.count());
        health.put("memory", Map.of(
                "free", runtime.freeMemory(),
                "total", runtime.totalMemory(),
                "max", runtime.maxMemory()
        ));
        health.put("uptime", String.format("%dd %dh %dm %ds",
                uptime.toDays(), uptime.toHoursPart(), uptime.toMinutesPart(), uptime.toSecondsPart()));
        return health;
    }

    // ── VULNERABILITY 4: Information disclosure ──────────────────────
    // Exposes internal system details — ZAP and Semgrep should catch this
    @GetMapping("/debug")
    public Map<String, Object> debug() {
        return Map.of(
                "javaVersion", System.getProperty("java.version"),
                "osName", System.getProperty("os.name"),
                "userDir", System.getProperty("user.dir"),
                "freeMemory", Runtime.getRuntime().freeMemory(),
                "secret", API_SECRET
        );
    }

    // ── VULNERABILITY 5: Open redirect ───────────────────────────────
    // No validation on the redirect target — ZAP will flag this
    @GetMapping("/redirect")
    public void unsafeRedirect(@RequestParam String url,
                               HttpServletResponse response) throws IOException {
        response.sendRedirect(url);
    }

    // ── VULNERABILITY 6: Verbose error with stack trace ──────────────
    // Returns raw exception details to the caller
    @GetMapping("/error-demo")
    public Product triggerError() {
        throw new RuntimeException(
                "Database connection failed: jdbc:h2:mem:testdb, user=sa, password=secret123"
        );
    }
}
