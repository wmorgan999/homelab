package com.lab.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/customers")
public class CustomerController {
    private static final Logger log = LoggerFactory.getLogger(CustomerController.class);
    private static final String TOPIC = "customer-events";

    private final CustomerRepository repo;
    private final KafkaTemplate<String, String> kafka;
    private final ObjectMapper mapper;

    public CustomerController(CustomerRepository repo, KafkaTemplate<String, String> kafka, ObjectMapper mapper) {
        this.repo = repo;
        this.kafka = kafka;
        this.mapper = mapper;
    }

    @GetMapping
    public List<Customer> all() {
        return repo.findAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Customer> one(@PathVariable Long id) {
        return repo.findById(id).map(ResponseEntity::ok)
                   .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public Customer create(@RequestBody Customer c) {
        Customer saved = repo.save(c);
        publish("CUSTOMER_CREATED", saved);
        return saved;
    }

    @PutMapping("/{id}")
    public ResponseEntity<Customer> update(@PathVariable Long id, @RequestBody Customer body) {
        return repo.findById(id).map(existing -> {
            existing.setName(body.getName());
            existing.setEmail(body.getEmail());
            // saveAndFlush sends the UPDATE now, so a duplicate email fails here
            // (and reaches the handler below) instead of at some later commit.
            Customer saved = repo.saveAndFlush(existing);
            publish("CUSTOMER_UPDATED", saved);
            return ResponseEntity.ok(saved);
        }).orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        return repo.findById(id).map(existing -> {
            repo.delete(existing);
            publish("CUSTOMER_DELETED", existing);
            return ResponseEntity.<Void>noContent().build();
        }).orElse(ResponseEntity.notFound().build());
    }

    // A unique-constraint violation used to surface as a generic 500.
    // Now the client gets 409 Conflict with a message it can show.
    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<Map<String, String>> integrity(DataIntegrityViolationException e) {
        String cause = String.valueOf(e.getMostSpecificCause().getMessage());
        if (cause.contains("email")) {
            return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(Map.of("error", "That email is already registered."));
        }
        return ResponseEntity.badRequest().body(Map.of("error", "Invalid customer data."));
    }

    // Best effort: the database change has already happened, so a Kafka problem
    // is logged, not returned to the caller (same behaviour create() always had).
    private void publish(String type, Customer c) {
        try {
            String json = mapper.writeValueAsString(Map.of(
                "type", type,
                "id", c.getId(),
                "name", c.getName(),
                "email", c.getEmail()));
            kafka.send(TOPIC, String.valueOf(c.getId()), json);
        } catch (Exception e) {
            log.warn("Could not publish customer event", e);
        }
    }
}
