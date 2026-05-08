type StatusMessageProps = {
  title: string;
  detail?: string;
  tone?: "neutral" | "error" | "success";
};

export function StatusMessage({ title, detail, tone = "neutral" }: StatusMessageProps) {
  return (
    <div data-tone={tone}>
      <strong>{title}</strong>
      {detail ? <p>{detail}</p> : null}
    </div>
  );
}
