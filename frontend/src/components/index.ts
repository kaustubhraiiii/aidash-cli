// Shared termcn component wrappers. Thin re-exports; views import from here so
// swapping the underlying lib later touches one file.
//
// TODO(termcn): the entire @termcn/* scope is unpublished on the public npm
// registry (table, bar-chart, spinner, alert, badge all 404 as of 2026-06-06).
// The intended exports are stubbed below until the source of these packages is
// resolved (private registry, rename, or hand-built wrappers). Views currently
// render with `ink` primitives directly and do not import this barrel yet, so
// these stubs do not affect the build.
//
//   export { default as Table } from "@termcn/table";
//   export { default as BarChart } from "@termcn/bar-chart";
//   export { default as Spinner } from "@termcn/spinner";
//   export { default as Alert } from "@termcn/alert";
//   export { default as Badge } from "@termcn/badge";

export {};
