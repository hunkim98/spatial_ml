import { ReactNode } from "react";
import { useRouter } from "next/router";
import {
  AppShell,
  Group,
  Title,
  ThemeIcon,
  Button,
  Divider,
} from "@mantine/core";
import { IconMapPin } from "@tabler/icons-react";

interface LayoutProps {
  children: ReactNode;
  sidebar?: ReactNode;
  hideHeader?: boolean;
}

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/labeller", label: "Editor" },
  { href: "/demo", label: "Demo" },
];

export function Layout({ children, sidebar, hideHeader }: LayoutProps) {
  const router = useRouter();

  // For landing page, render without AppShell header
  if (hideHeader) {
    return <>{children}</>;
  }

  return (
    <AppShell
      header={{ height: 50 }}
      navbar={sidebar ? { width: 300, breakpoint: "sm" } : undefined}
      padding={0}
    >
      {/* Top Navigation Bar */}
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <ThemeIcon
              size="md"
              variant="gradient"
              gradient={{ from: "cyan", to: "teal" }}
            >
              <IconMapPin size={16} />
            </ThemeIcon>
            <Title order={5}>Spatially</Title>
            <Divider orientation="vertical" mx="xs" />
            <Group gap={4}>
              {NAV_ITEMS.map((item) => (
                <Button
                  key={item.href}
                  variant={router.pathname === item.href ? "light" : "subtle"}
                  size="compact-sm"
                  onClick={() => router.push(item.href)}
                >
                  {item.label}
                </Button>
              ))}
            </Group>
          </Group>
        </Group>
      </AppShell.Header>

      {/* Left Sidebar (optional, for tools) */}
      {sidebar && (
        <AppShell.Navbar p="sm" style={{ overflow: "auto" }}>
          {sidebar}
        </AppShell.Navbar>
      )}

      <AppShell.Main style={{ height: "calc(100vh - 50px)" }}>
        {children}
      </AppShell.Main>
    </AppShell>
  );
}
