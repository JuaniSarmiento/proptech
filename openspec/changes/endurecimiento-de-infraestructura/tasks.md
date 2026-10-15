Convención: en cada tarea el test va primero y se lo ve fallar (RED) antes del código (GREEN); el paso
rojo es obligatorio y se anota en el informe con el comando y su salida. "Verde" quiere decir lint,
formato, tipos y tests del lado tocado (L-005), más `shellcheck` sobre todo script de Bash tocado. Para
ver fallar una verificación contra configuración mutada a propósito, se muta una copia o se saca antes
una copia del original y se compara con un diff real (L-013). Cada tarea nombra los escenarios de la
spec que cubre y las lecciones que aplica. Ninguna tarea supera medio día.

Precondiciones: el 2a (`aislamiento-por-administracion`) archivado. Gobernanza MEDIUM: sin aprobación
previa de un socio; las decisiones no obvias (la lista de capacidades, el digest) van en el informe.

## 1. Línea de base

- [ ] 1.1 Correr la suite completa antes de tocar nada (`bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh`, `bash infra/ci/humo.sh`, en ese orden y de a uno, D7) y anotar la cantidad de tests de cada lado, con la hora y el commit; si algo falla, frenar e informarlo como falla previa. Escenarios: ninguno. Lecciones: L-003.

## 2. Proxy y contenedores

- [ ] 2.1 Cabeceras y volúmenes (D1, D2) en `tests/infra/test_caddyfile_seguridad.py` y `tests/infra/test_compose.py`: el `Caddyfile` fija las cuatro cabeceras y quita `Server`, `Via` y `X-Powered-By`, también con `header_down` en cada `reverse_proxy`; `web/next.config.ts` tiene `poweredByHeader: false`; Caddy monta `datos_caddy:/data` y `config_caddy:/config`. Verlos fallar, implementar, verlos pasar (la verificación de punta a punta es 4.3). Escenarios: `entorno-de-ejecucion` › Respuesta de la web y de la API (la parte estática); › Caddy reinicia sin perder certificados. Lecciones: L-004.
- [ ] 2.2 Privilegios y capacidades (D3) en `tests/infra/test_compose.py`: todos los servicios con `no-new-privileges` y `cap_drop: [ALL]`; `cap_add` sólo en `db`, `redis` y `caddy`, igual a la lista fijada. Para fijarla, levantar el stack sin cada capacidad candidata (sobre una copia de Compose, L-013) y anotar cuál hizo falta y el error que dio; la que no hizo falta no entra. Escenarios: `entorno-de-ejecucion` › Privilegios y capacidades. Lecciones: L-013.
- [ ] 2.3 PID 1 no root servicio por servicio (D4): el chequeo del humo se aplica a `api`, `worker`, `web`, `migraciones` y `respaldos`; el rojo se ve **en cada uno** con una copia de Compose que lo pone como `user: "0:0"`, y se anota la salida de los cinco rojos. Escenarios: `entorno-de-ejecucion` › PID 1 de cada servicio. Lecciones: L-013, L-016.

## 3. CI

- [ ] 3.1 CI (D5) en `tests/infra/test_ci_workflow.py`: el workflow se dispara con `push` y `pull_request`, cada trabajo tiene `timeout-minutes` y la imagen de gitleaks lleva `@sha256:` con el digest anotado junto al comando que lo obtuvo. Verlo fallar, implementar, verlo pasar. Escenarios: `integracion-continua` › Workflow revisado. Lecciones: L-005.

## 4. Humo

- [ ] 4.1 Pasos con nombre y "uno solo" exacto (D6): `paso N "descripción"` y su `if ! ...; then` en cada paso, incluidos el 11 y el 13 del 1d; `exactamente_uno` en cada "aparece uno solo", visto en rojo con dos apariciones (sobre una copia, L-013); en `tests/infra/test_humo.py`, que cada paso del texto del humo tenga su `paso` y que no quede ningún "uno solo" sin `exactamente_uno`. Escenarios: `integracion-continua` › Un paso que falla; › Uno solo. Lecciones: L-013, L-014, L-016.
- [ ] 4.2 Doble congelada (D6): `pause db redis` a la vez con un `trap` que despausa siempre; `/api/salud` 503 en menos de 2 s, exactamente dos `salud_degradada` con el `request_id`, `/salud-web` sin `sin_conexion`; verificar que después del paso `db` y `redis` responden, también cuando se fuerza la falla del paso. Escenarios: `integracion-continua` › Base y Redis congelados. Lecciones: L-001, L-014.
- [ ] 4.3 Cabeceras de punta a punta (D6): GET y HEAD a `/` y `/api/salud` y GET a una ruta inexistente de la API, por el proxy; las cabeceras de seguridad presentes, `Server`, `Via` y `X-Powered-By` ausentes, HEAD sin cuerpo. Verlo fallar antes de 2.1. Escenarios: `integracion-continua` › Cabeceras en el stack vivo; `entorno-de-ejecucion` › Respuesta de la web y de la API; › Respuesta de error de la API. Lecciones: L-004.

## 5. Documentación

- [ ] 5.1 README (D8): la tabla completa de variables. Test en `tests/infra/test_readme_variables.py` que exige que cada variable de `infra/.env.example` aparezca en la tabla; verlo fallar antes. Escenarios: ninguno (documentación). Lecciones: L-005.

## 6. Cierre

- [ ] 6.1 **Después de la última vuelta de correcciones** (L-010): `bash infra/ci/test-backend.sh`, `bash infra/ci/test-web.sh` y `bash infra/ci/humo.sh` **en ese orden y de a uno** (D7); anotar la cantidad de tests contra la línea de base de 1.1, con hora y commit; repetirla si el código cambia después. Escenarios: todos. Lecciones: L-003, L-005, L-010.
