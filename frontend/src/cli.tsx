import { render, Text } from "ink";
import { ThemeProvider } from "@/components/ui/theme-provider";
import { defaultTheme } from "@/lib/terminal-themes/default";
import { CostView } from "./views/cost.js";
import { ReplayView } from "./views/replay.js";
import { ScoreView } from "./views/score.js";
import { RatesView } from "./views/rates.js";
import { SearchView } from "./views/search.js";

const VIEWS = {
  cost: CostView,
  replay: ReplayView,
  score: ScoreView,
  rates: RatesView,
  search: SearchView,
} as const;

type Cmd = keyof typeof VIEWS;

function main() {
  const [command, ...args] = process.argv.slice(2);

  if (!command || !(command in VIEWS)) {
    render(
      <Text>aidash-ui — usage: aidash-ui &lt;{Object.keys(VIEWS).join(" | ")}&gt; [args]</Text>,
    );
    process.exitCode = command ? 1 : 0;
    return;
  }

  const View = VIEWS[command as Cmd];
  render(
    <ThemeProvider theme={defaultTheme}>
      <View args={args} />
    </ThemeProvider>,
  );
}

main();
