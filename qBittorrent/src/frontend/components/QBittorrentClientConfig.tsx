import { useState } from "react";
import { TextInput, NumberInput, Button, Stack, Group, Switch, PasswordInput } from "@mantine/core";
import type { DownloadClientConfigProps } from "../../../types/Plugin";

export function QBittorrentClientConfig({ client, pluginId, onSave, onCancel }: DownloadClientConfigProps) {
  const [name, setName] = useState(client?.name || "");
  const [description, setDescription] = useState(client?.description || "");
  const [host, setHost] = useState((client?.config?.host as string) || "");
  const [port, setPort] = useState((client?.config?.port as number) || 8080);
  const [username, setUsername] = useState((client?.config?.username as string) || "");
  const [password, setPassword] = useState((client?.config?.password as string) || "");
  const [useSsl, setUseSsl] = useState((client?.config?.use_ssl as boolean) ?? false);
  const [enabled, setEnabled] = useState(client?.enabled ?? true);
  const [isDefault, setIsDefault] = useState(client?.is_default ?? false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    await onSave({
      name,
      description,
      version: "0.1.0",
      enabled,
      is_default: isDefault,
      config: {
        host,
        port,
        username,
        password,
        use_ssl: useSsl,
      },
      plugin_id: client?.plugin_id || pluginId,
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="md">
        <TextInput
          label="Name"
          placeholder="My qBittorrent Client"
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
          label="Host"
          placeholder="localhost or IP address"
          required
          value={host}
          onChange={(e) => setHost(e.currentTarget.value)}
        />

        <NumberInput
          label="Port"
          placeholder="8080"
          required
          min={1}
          max={65535}
          value={port}
          onChange={(val) => setPort(Number(val))}
        />

        <TextInput
          label="Username"
          placeholder="admin"
          required
          value={username}
          onChange={(e) => setUsername(e.currentTarget.value)}
        />

        <PasswordInput
          label="Password"
          placeholder="Your password"
          required
          value={password}
          onChange={(e) => setPassword(e.currentTarget.value)}
        />

        <Switch
          label="Use SSL/HTTPS"
          checked={useSsl}
          onChange={(e) => setUseSsl(e.currentTarget.checked)}
        />

        <Switch
          label="Set as Default Client"
          description="This will be used as the primary download client"
          checked={isDefault}
          onChange={(e) => setIsDefault(e.currentTarget.checked)}
        />

        <Switch
          label="Enabled"
          checked={enabled}
          onChange={(e) => setEnabled(e.currentTarget.checked)}
        />

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onCancel}>
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
