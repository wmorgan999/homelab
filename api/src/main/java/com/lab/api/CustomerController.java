package com.lab.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
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
        try {
            String json = mapper.writeValueAsString(Map.of(
                "type", "CUSTOMER_CREATED",
                "id", saved.getId(),
                "name", saved.getName(),
                "email", saved.getEmail()));
            kafka.send(TOPIC, String.valueOf(saved.getId()), json);
        } catch (Exception e) {
            log.warn("Could not publish customer event", e);
        }
        return saved;
    }
}
