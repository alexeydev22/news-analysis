import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the chat console controls and empty state", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Economic News Dialog" })).toBeInTheDocument();
    expect(screen.getByLabelText("Модель анализа")).toBeInTheDocument();
    expect(screen.getByLabelText("Лимит источников")).toBeInTheDocument();
    expect(screen.getByLabelText("Источник")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview CSV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Index CSV" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Вопрос" })).toBeInTheDocument();
    expect(screen.getByText("Ответ появится после отправки вопроса.")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Источники анализа" })).toBeInTheDocument();
    expect(screen.getByText("Источники появятся после ответа.")).toBeInTheDocument();
  });

  it("keeps the composer submission inside the single-page app", async () => {
    const user = userEvent.setup();
    render(<App />);

    const form = screen.getByRole("form", { name: "Форма вопроса" });
    const question = screen.getByRole("textbox", { name: "Вопрос" });

    await user.type(question, "Что означает рост ВВП?");

    const submitEvent = new SubmitEvent("submit", { bubbles: true, cancelable: true });

    expect(form.dispatchEvent(submitEvent)).toBe(false);
    expect(question).toHaveValue("Что означает рост ВВП?");
  });
});
