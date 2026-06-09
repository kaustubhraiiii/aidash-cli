// Shared termcn component barrel. Components are vendored under ui/ via the
// shadcn CLI (`npx shadcn@latest add @termcn/<name>`) and registered through
// frontend/components.json. Views import from here so the component surface
// lives in one place.
export { Table } from "@/components/ui/table";
export { BarChart } from "@/components/ui/bar-chart";
export { Spinner } from "@/components/ui/spinner";
export { Alert } from "@/components/ui/alert";
export { Badge } from "@/components/ui/badge";
export { TokenUsage, ContextMeter } from "@/components/ui/token-usage";
export { ToolCall } from "@/components/ui/tool-call";
export { ThemeProvider, useTheme } from "@/components/ui/theme-provider";
