import { useMemo } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

/**
 * Renderiza la `notacion()` de una regla (LaTeX) como matemática formateada.
 * El backend es la única fuente de la notación; acá solo se muestra (KaTeX).
 */
export function Notacion({ tex }: { tex: string | null }) {
  const html = useMemo(() => {
    if (!tex) return null;
    try {
      return katex.renderToString(tex, { displayMode: true, throwOnError: false });
    } catch {
      return null;
    }
  }, [tex]);

  if (!html) return <p className="notacion-vacia">— sin notación —</p>;
  // KaTeX sanea su propia salida; dangerouslySetInnerHTML es el uso estándar.
  return <div className="notacion" dangerouslySetInnerHTML={{ __html: html }} />;
}
