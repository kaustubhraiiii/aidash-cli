import { Box, Text } from "ink";

const COMMANDS: { name: string; description: string }[] = [
  { name: "cost", description: "session cost breakdown" },
  { name: "replay", description: "replay a session timeline" },
  { name: "score", description: "session quality score" },
  { name: "rates", description: "model pricing rates" },
  { name: "search", description: "search sessions by query" },
];

export function HelpView({ args: _args }: { args?: string[] }) {
  return (
    <Box flexDirection="column" gap={1}>
      <Text bold>aidash — AI usage dashboard</Text>
      <Box flexDirection="column">
        {COMMANDS.map((cmd) => (
          <Box key={cmd.name} flexDirection="row" gap={2}>
            <Text bold color="cyan">
              {cmd.name.padEnd(10)}
            </Text>
            <Text dimColor>{cmd.description}</Text>
          </Box>
        ))}
      </Box>
      <Text dimColor>Usage: aidash-ui {"<command>"} [args]</Text>
    </Box>
  );
}
