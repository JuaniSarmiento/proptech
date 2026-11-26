/*
 * Service worker mínimo de PropTech (H-040, D-170.6). Existe para que la app sea instalable y para nada
 * más: NO guarda nada. No hay modo sin conexión: lo que muestra el portal es plata y datos de la
 * persona, y una copia guardada en el teléfono puede quedar vieja o a la vista de otra persona que use
 * ese aparato. Por eso no abre ninguna caché, no responde pedidos (cada uno sigue a la red, `/api`
 * incluido) y, al activarse, borra cualquier caché que hubiera dejado otra versión.
 */
self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((nombres) => Promise.all(nombres.map((nombre) => caches.delete(nombre))))
      .then(() => self.clients.claim()),
  );
});

// Un `fetch` sin `respondWith`: el navegador sigue con su pedido normal, directo a la red.
self.addEventListener("fetch", () => {});
