import { defineConfig } from "tsup";
import { fileURLToPath } from "node:url";

// Bundle our own source into a single runnable ESM file. esbuild resolves the
// "@/" path alias (used by the vendored termcn components) to ./src, while npm
// dependencies (ink, react, cli-spinners, ...) stay external and resolve from
// node_modules at runtime. Raw `tsc` emit would leave "@/..." specifiers that
// Node cannot resolve.
export default defineConfig({
  entry: ["src/cli.tsx"],
  format: ["esm"],
  target: "node18",
  outDir: "dist",
  clean: true,
  banner: { js: "#!/usr/bin/env node" },
  esbuildOptions(options) {
    options.alias = {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    };
  },
});
