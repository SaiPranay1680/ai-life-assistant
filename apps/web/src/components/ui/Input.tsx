"use client";

import { cn } from "@/utils";
import { Eye, EyeOff } from "lucide-react";
import { useState, type InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  showPasswordToggle?: boolean;
};

export function Input({
  label,
  error,
  id,
  className,
  type,
  showPasswordToggle = true,
  ...props
}: InputProps) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";
  const inputId = id ?? props.name ?? label.toLowerCase().replace(/\s+/g, "-");

  const effectiveType =
    isPassword && showPasswordToggle ? (showPassword ? "text" : "password") : type;

  return (
    <label className="block text-left" htmlFor={inputId}>
      <span className="mb-1.5 block text-sm font-semibold text-slate-800">
        {label}
      </span>
      <div className="relative">
        <input
          id={inputId}
          type={effectiveType}
          className={cn(
            "w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-50 disabled:text-slate-600",
            isPassword && showPasswordToggle ? "pr-10" : "",
            error ? "border-rose-400" : "border-slate-200",
            className,
          )}
          {...props}
        />
        {isPassword && showPasswordToggle ? (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-600 focus:outline-none"
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Eye className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        ) : null}
      </div>
      {error ? <span className="mt-1 block text-xs text-rose-600">{error}</span> : null}
    </label>
  );
}
