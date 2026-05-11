import { useState } from "react";

import styles from "../app/App.module.css";

type NewsDetailsProps = {
  title: string;
  text: string;
};

export function NewsDetails({ title, text }: NewsDetailsProps) {
  const [isExpanded, setExpanded] = useState(false);

  if (!text.trim()) {
    return null;
  }

  return (
    <div className={styles.newsDetails}>
      <button
        type="button"
        className={styles.ghostButton}
        aria-expanded={isExpanded}
        aria-label={`${isExpanded ? "Скрыть" : "Показать"} полный текст новости ${title}`}
        onClick={() => setExpanded((current) => !current)}
      >
        {isExpanded ? "Скрыть текст" : "Показать полный текст"}
      </button>
      {isExpanded ? <p className={styles.newsFullText}>{text}</p> : null}
    </div>
  );
}
