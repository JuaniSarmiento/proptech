// Sólo vitest: las pruebas del cliente siguen usando fetch real o su propio doble.
import { vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("@clerk/nextjs/server", () => ({
  auth: vi.fn(async () => ({ userId: "user_prueba", getToken: async () => "token-local" })),
}));
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({
    get: () => ({ value: "10000000-0000-0000-0000-000000000001" }),
    set: vi.fn(),
  })),
  headers: vi.fn(async () => new Headers({ "x-proptech-ruta": "/edificios" })),
}));
