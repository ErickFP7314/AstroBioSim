import { useEffect, useMemo, useState } from "react";
import {
  fetchValidarRegla,
  type Catalogo,
  type Clausula,
  type Condicion,
  type ProbId,
  type ReglaSpec,
  type ResultadoId,
  type ValidacionRegla,
  type Vocabulario,
} from "../api";
import { ESTADO_COLOR } from "../theme";

// Editor visual de reglas por bloques (ADR-0018). Cada regla es una lista de
// filas "SI <condiciones> → <estado>"; se evalúan en orden y la PRIMERA que
// matchea gana. El editor no ejecuta nada: arma el spec y lo valida en el
// backend (única fuente de verdad de la notación).

const RESULTADO_INT: Record<ResultadoId, 0 | 1 | 2> = { MUERTA: 0, LATENTE: 1, ACTIVA: 2 };

const clonar = (s: ReglaSpec): ReglaSpec => JSON.parse(JSON.stringify(s));

interface Props {
  vocabulario: Vocabulario;
  presets: Catalogo["reglas"];
  specInicial: ReglaSpec;
  onUsar: (spec: ReglaSpec) => void;
  onCerrar: () => void;
}

export function RuleEditor({ vocabulario, presets, specInicial, onUsar, onCerrar }: Props) {
  const [spec, setSpec] = useState<ReglaSpec>(() => clonar(specInicial));
  const [val, setVal] = useState<ValidacionRegla | null>(null);

  // Valida en el backend con debounce mientras se edita.
  useEffect(() => {
    const id = window.setTimeout(() => {
      fetchValidarRegla(spec).then(setVal).catch(() => setVal(null));
    }, 300);
    return () => window.clearTimeout(id);
  }, [spec]);

  const camposDe = useMemo(
    () => (tipo: string) => vocabulario.condiciones.find((c) => c.tipo === tipo)!.campos,
    [vocabulario],
  );
  const condicionDefault = (tipo: string): Condicion => {
    const campos = camposDe(tipo);
    const base: Record<string, unknown> = { tipo };
    for (const k of Object.keys(campos)) base[k] = campos[k][0].id;
    return base as Condicion;
  };

  // --- mutadores inmutables ---
  const conClausulas = (fn: (cl: Clausula[]) => Clausula[]) =>
    setSpec((s) => ({ ...s, clausulas: fn(s.clausulas.map((c) => ({ ...c }))) }));
  const setClausula = (i: number, patch: Partial<Clausula>) =>
    conClausulas((cl) => cl.map((c, k) => (k === i ? { ...c, ...patch } : c)));
  const addClausula = () =>
    conClausulas((cl) => [...cl, { cuando: [], entonces: "MUERTA" as ResultadoId }]);
  const delClausula = (i: number) => conClausulas((cl) => cl.filter((_, k) => k !== i));
  const moverClausula = (i: number, d: number) =>
    conClausulas((cl) => {
      const j = i + d;
      if (j < 0 || j >= cl.length) return cl;
      const copia = [...cl];
      [copia[i], copia[j]] = [copia[j], copia[i]];
      return copia;
    });
  const setCondiciones = (i: number, cuando: Condicion[]) => setClausula(i, { cuando });

  const usable = val?.valida ?? false;

  return (
    <div className="modal-bg" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Editor de regla">
        <header className="modal-head">
          <div>
            <p className="ttl">Editor de regla · bloques</p>
            <p className="sub">SI las condiciones se cumplen → estado. La primera fila que matchea gana.</p>
          </div>
          <button className="x" onClick={onCerrar} aria-label="Cerrar">✕</button>
        </header>

        <div className="modal-tools">
          <label className="fld">
            <span>Plantilla</span>
            <select
              onChange={(e) => {
                const p = presets.find((x) => x.id === e.target.value);
                if (p) setSpec(clonar(p.spec));
              }}
              value=""
            >
              <option value="" disabled>cargar preset…</option>
              {presets.map((p) => (
                <option key={p.id} value={p.id}>{p.nombre}</option>
              ))}
            </select>
          </label>
          <label className="fld grow">
            <span>Nombre</span>
            <input
              type="text"
              value={spec.nombre}
              onChange={(e) => setSpec((s) => ({ ...s, nombre: e.target.value }))}
            />
          </label>
        </div>

        <ol className="clausulas">
          {spec.clausulas.map((cl, i) => (
            <li className="clausula" key={i}>
              <span className="idx">{i + 1}</span>
              <span className="si">SI</span>
              <div className="conds">
                {cl.cuando.length === 0 && <span className="vacio">en otro caso</span>}
                {cl.cuando.map((cond, j) => (
                  <Chip
                    key={j}
                    voc={vocabulario}
                    camposDe={camposDe}
                    cond={cond}
                    onCambiarTipo={(tipo) =>
                      setCondiciones(i, cl.cuando.map((c, k) => (k === j ? condicionDefault(tipo) : c)))
                    }
                    onCambiarCampo={(campo, valor) =>
                      setCondiciones(
                        i,
                        cl.cuando.map((c, k) => (k === j ? ({ ...c, [campo]: valor } as Condicion) : c)),
                      )
                    }
                    onQuitar={() => setCondiciones(i, cl.cuando.filter((_, k) => k !== j))}
                  />
                ))}
                <button
                  className="add-cond"
                  onClick={() => setCondiciones(i, [...cl.cuando, condicionDefault("estado")])}
                >
                  + condición
                </button>
              </div>

              <span className="flecha">→</span>
              <select
                className="res"
                style={{ color: ESTADO_COLOR[RESULTADO_INT[cl.entonces]] }}
                value={cl.entonces}
                onChange={(e) => setClausula(i, { entonces: e.target.value as ResultadoId })}
              >
                {vocabulario.resultados.map((r) => (
                  <option key={String(r.id)} value={String(r.id)}>{r.label}</option>
                ))}
              </select>

              <select
                className="prob"
                value={JSON.stringify(cl.prob ?? null)}
                onChange={(e) => setClausula(i, { prob: JSON.parse(e.target.value) as ProbId })}
                title="Probabilidad de la transición"
              >
                {vocabulario.probabilidades.map((p) => (
                  <option key={String(p.id)} value={JSON.stringify(p.id)}>{p.label}</option>
                ))}
              </select>

              <div className="fila-acc">
                <button onClick={() => moverClausula(i, -1)} disabled={i === 0} aria-label="Subir">↑</button>
                <button onClick={() => moverClausula(i, 1)} disabled={i === spec.clausulas.length - 1} aria-label="Bajar">↓</button>
                <button onClick={() => delClausula(i)} disabled={spec.clausulas.length <= 1} aria-label="Borrar">🗑</button>
              </div>
            </li>
          ))}
        </ol>

        <button className="add-fila" onClick={addClausula}>+ agregar fila</button>

        <div className={"val " + (val ? (val.valida ? "ok" : "bad") : "")}>
          {val === null && "validando…"}
          {val?.valida && "✓ regla válida"}
          {val && !val.valida && `✕ ${val.error}`}
        </div>

        <footer className="modal-foot">
          <button className="ghost" onClick={onCerrar}>Cancelar</button>
          <button className="run" disabled={!usable} onClick={() => onUsar(spec)}>
            Usar esta regla
          </button>
        </footer>
      </div>
    </div>
  );
}

// --- chip de una condición ---
function Chip(props: {
  voc: Vocabulario;
  camposDe: (t: string) => Record<string, { id: string | number | boolean | null; label: string }[]>;
  cond: Condicion;
  onCambiarTipo: (tipo: string) => void;
  onCambiarCampo: (campo: string, valor: unknown) => void;
  onQuitar: () => void;
}) {
  const { voc, camposDe, cond, onCambiarTipo, onCambiarCampo, onQuitar } = props;
  const campos = camposDe(cond.tipo);
  return (
    <span className="cond">
      <select
        className="c-tipo"
        value={cond.tipo}
        onChange={(e) => onCambiarTipo(e.target.value)}
      >
        {voc.condiciones.map((c) => (
          <option key={c.tipo} value={c.tipo}>{c.label}</option>
        ))}
      </select>
      {Object.keys(campos).map((campo) => (
        <select
          key={campo}
          value={JSON.stringify((cond as Record<string, unknown>)[campo])}
          onChange={(e) => onCambiarCampo(campo, JSON.parse(e.target.value))}
        >
          {campos[campo].map((o, i) => (
            <option key={i} value={JSON.stringify(o.id)}>{o.label}</option>
          ))}
        </select>
      ))}
      <button className="c-x" onClick={onQuitar} aria-label="Quitar condición">×</button>
    </span>
  );
}
