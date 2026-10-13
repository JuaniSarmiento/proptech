## MODIFIED Requirements

### Requirement: Prueba de humo del stack detrás del proxy

El CI SHALL levantar el stack completo con Compose y verificar que `GET /api/salud` a través del
proxy responde 200 con la base y la cola conectadas, que el único servicio con puertos publicados es
el proxy, que el worker está saludable y completa un trabajo con un reintento, que el `request_id`
asignado por el proxy aparece en el log de la API tanto en un pedido directo como en uno que pasa por
la web, que un backup se generó solo, que ese backup se restaura en una base aparte y que sobrevive a
`docker compose down -v`. Todo comando destructivo del humo MUST apuntar al proyecto de Compose
`proptech` o a bases con el prefijo `proptech_`.

#### Scenario: Humo en el CI

- **WHEN** corre el paso de humo
- **THEN** el stack se levanta, el endpoint de salud responde 200 a través del proxy, la verificación
  de puertos publicados pasa, el `request_id` se sigue de punta a punta, el backup automático aparece
  y se restaura, y el stack se baja al terminar, aun si el paso falló

#### Scenario: Request id malicioso en el humo

- **WHEN** el humo manda un pedido con un `X-Request-ID` malicioso a través del proxy
- **THEN** la respuesta trae un UUID distinto y el valor malicioso no aparece en los logs de ningún
  servicio

#### Scenario: Redis pausado en el humo

- **WHEN** el humo pausa Redis y consulta `GET /api/salud` a través del proxy
- **THEN** la respuesta es 503 con `"cola": "sin_conexion"` en menos de 4 segundos, y Redis se
  despausa aunque la verificación falle
