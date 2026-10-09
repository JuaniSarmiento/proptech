import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import Page from "./page";

describe("página técnica", () => {
  it("muestra el texto PropTech", () => {
    const html = renderToStaticMarkup(<Page />);
    expect(html).toContain("PropTech");
  });
});
