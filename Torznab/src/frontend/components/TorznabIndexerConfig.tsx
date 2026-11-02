import { useState } from "react";
import { TextInput, NumberInput, Button, Stack, Group, Switch, PasswordInput, Alert } from "@mantine/core";
import { TbCheck, TbX } from "react-icons/tb";
import type { IndexerConfigProps } from "../../../types/Plugin";
import { testIndexerConnection } from "../../../api/api";

export function TorznabIndexerConfig({ indexer, pluginId, onSave, onCancel }: IndexerConfigProps) {
  const [name, setName] = useState(indexer?.name || "");
  const [description, setDescription] = useState(indexer?.description || "");
  const [url, setUrl] = useState((indexer?.config?.url as string) || "");
  const [apiKey, setApiKey] = useState((indexer?.config?.api_key as string) || "");
  const [priority, setPriority] = useState((indexer?.config?.priority as number) || 25);
  const [enabled, setEnabled] = useState(indexer?.enabled ?? true);
  const [supportsRss, setSupportsRss] = useState((indexer?.config?.supports_rss as boolean) ?? true);
  const [supportsSearch, setSupportsSearch] = useState((indexer?.config?.supports_search as boolean) ?? true);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleTestConnection = async () => {
    if (!url) {
      setTestResult({ success: false, message: "Please enter a URL first" });
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      const result = await testIndexerConnection({
        plugin_id: pluginId,
        config: {
          url,
          api_key: apiKey,
          priority,
          supports_rss: supportsRss,
          supports_search: supportsSearch,
        },
      });

      setTestResult(result);
    } catch (error) {
      setTestResult({ 
        success: false, 
        message: `Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}` 
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    await onSave({
      name,
      description,
      version: "1.0.0",
      enabled,
      config: {
        url,
        api_key: apiKey,
        priority,
        supports_rss: supportsRss,
        supports_search: supportsSearch,
      },
      plugin_id: indexer?.plugin_id,
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="md">
        <TextInput
          label="Name"
          placeholder="My Torznab Indexer"
          required
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
        />

        <TextInput
          label="Description"
          placeholder="Optional description"
          value={description}
          onChange={(e) => setDescription(e.currentTarget.value)}
        />

        <TextInput
          label="Torznab URL"
          placeholder="https://example.com/torznab"
          required
          value={url}
          onChange={(e) => setUrl(e.currentTarget.value)}
        />

        <PasswordInput
          label="API Key"
          placeholder="Your API key"
          value={apiKey}
          onChange={(e) => setApiKey(e.currentTarget.value)}
        />

        <Group justify="space-between" align="flex-end">
          <div style={{ flex: 1 }}>
            {testResult && (
              <Alert
                icon={testResult.success ? <TbCheck size={16} /> : <TbX size={16} />}
                color={testResult.success ? "green" : "red"}
                variant="light"
              >
                {testResult.message}
              </Alert>
            )}
          </div>
          <Button
            variant="light"
            onClick={handleTestConnection}
            loading={testing}
            disabled={!url}
          >
            Test Connection
          </Button>
        </Group>

        <NumberInput
          label="Priority"
          description="Lower numbers have higher priority"
          min={1}
          max={100}
          value={priority}
          onChange={(val) => setPriority(Number(val))}
        />

        <Switch
          label="RSS Feed Support"
          checked={supportsRss}
          onChange={(e) => setSupportsRss(e.currentTarget.checked)}
        />

        <Switch
          label="Interactive Search Support"
          checked={supportsSearch}
          onChange={(e) => setSupportsSearch(e.currentTarget.checked)}
        />

        <Switch
          label="Enabled"
          checked={enabled}
          onChange={(e) => setEnabled(e.currentTarget.checked)}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="subtle" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit">
            Save
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
