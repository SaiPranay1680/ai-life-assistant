"use client";

import { useMemo } from "react";

export function OtpInput({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (next: string) => void;
  disabled?: boolean;
}) {
  const digits = useMemo(() => Array.from({ length: 6 }, (_, i) => value[i] ?? ""), [value]);

  function updateAt(index: number, char: string) {
    const cleaned = char.replace(/\D/g, "").slice(-1);
    const next = digits.map((digit, i) => (i === index ? cleaned : digit)).join("");
    onChange(next.slice(0, 6));
    if (cleaned) {
      const sibling = document.getElementById(`otp-${index + 1}`);
      sibling?.focus();
    }
  }

  return (
    <div className="flex justify-between gap-2" role="group" aria-label="Six-digit verification code">
      {digits.map((digit, index) => (
        <input
          key={index}
          id={`otp-${index}`}
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          maxLength={1}
          disabled={disabled}
          value={digit}
          onChange={(event) => updateAt(index, event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Backspace" && !digits[index] && index > 0) {
              document.getElementById(`otp-${index - 1}`)?.focus();
            }
          }}
          onPaste={(event) => {
            event.preventDefault();
            const pasted = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
            onChange(pasted);
          }}
          className="h-12 w-10 rounded-xl border border-slate-200 bg-white text-center text-lg font-semibold text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-50 sm:w-12"
        />
      ))}
    </div>
  );
}
