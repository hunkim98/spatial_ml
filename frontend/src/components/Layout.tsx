import { ReactNode } from "react";
import { useRouter } from "next/router";
import {
  AppShell,
  Group,
  Title,
  Button,
  Divider,
  Image,
} from "@mantine/core";

interface LayoutProps {
  children: ReactNode;
  sidebar?: ReactNode;
  hideHeader?: boolean;
}

const NAV_ITEMS = [
  { href: "/studio", label: "Studio" },
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
            <Image src="/icon.png" alt="Spatially" w={32} h={32} />
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
        <AppShell.Navbar
          p="sm"
          style={{
            display: "flex",
            flexDirection: "column" as const,
            overflow: "hidden",
          }}
        >
          {sidebar}
        </AppShell.Navbar>
      )}

      <AppShell.Main style={{ height: "calc(100vh - 50px)", overflow: "hidden" }}>
        {children}
      </AppShell.Main>
      {/* <AppShell.Main style={{}}>hi there</AppShell.Main> */}
    </AppShell>
  );
}
