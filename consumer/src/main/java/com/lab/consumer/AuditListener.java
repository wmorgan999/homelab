package com.lab.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class AuditListener {
    private static final Logger log = LoggerFactory.getLogger(AuditListener.class);

    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper = new ObjectMapper();

    public AuditListener(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @KafkaListener(topics = "customer-events")
    public void onEvent(String message) throws Exception {
        JsonNode node = mapper.readTree(message);
        String type = node.path("type").asText("UNKNOWN");
        jdbc.update("INSERT INTO customer_audit (event_type, payload) VALUES (?, ?::jsonb)", type, message);
        log.info("Audited event {}: {}", type, message);
    }
}
