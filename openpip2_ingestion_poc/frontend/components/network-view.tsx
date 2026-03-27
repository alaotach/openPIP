"use client";

import cytoscape from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";
import { useEffect, useRef, useState } from "react";

cytoscape.use(coseBilkent);

export function NetworkView() {
  const ref = useRef<HTMLDivElement | null>(null);
  const [selected, setSelected] = useState<string>("None");

  useEffect(() => {
    if (!ref.current) return;
    const cy = cytoscape({
      container: ref.current,
      elements: [
        { data: { id: "P12345", label: "P12345" } },
        { data: { id: "Q99999", label: "Q99999" } },
        { data: { id: "e1", source: "P12345", target: "Q99999" } },
      ],
      style: [
        { selector: "node", style: { "background-color": "#116466", label: "data(label)", color: "#fff", "text-valign": "center" } },
        { selector: "edge", style: { width: 2, "line-color": "#b9c8bf" } },
      ],
      layout: { name: "cose-bilkent", animate: false },
    });

    cy.on("tap", "node", (ev) => {
      setSelected(ev.target.data("label"));
    });

    return () => cy.destroy();
  }, []);

  return (
    <section className="card">
      <h2>PPI Network</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", gap: 12 }}>
        <div ref={ref} style={{ height: 300, border: "1px solid #e4e8e0", borderRadius: 10 }} />
        <aside className="card">
          <h3>Node Detail</h3>
          <p>{selected}</p>
        </aside>
      </div>
    </section>
  );
}
