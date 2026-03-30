import { useEffect } from "react";

const BASE_TITLE = "Cloak Haven";

export function useDocumentTitle(title?: string) {
  useEffect(() => {
    document.title = title ? `${title} — ${BASE_TITLE}` : `${BASE_TITLE} — The Global Standard for Digital Reputation`;
  }, [title]);
}
