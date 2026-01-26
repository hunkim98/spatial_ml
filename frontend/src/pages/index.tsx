import { Container, Title, Text, Card, SimpleGrid, ThemeIcon, Group } from "@mantine/core";
import { IconMap, IconDatabase, IconBrain } from "@tabler/icons-react";
import Link from "next/link";

const FEATURES = [
  {
    icon: IconMap,
    title: "PDF Labeller",
    description: "Georeference PDF maps by aligning them with satellite imagery. Create training data for ML models.",
    href: "/labeller",
  },
  {
    icon: IconDatabase,
    title: "Datasets",
    description: "Browse and manage labeled datasets. Export to various formats for training.",
    href: "#",
    disabled: true,
  },
  {
    icon: IconBrain,
    title: "Models",
    description: "Train and evaluate models for PDF to GeoJSON conversion.",
    href: "#",
    disabled: true,
  },
];

export default function Home() {
  return (
    <Container size="md" py="xl">
      <Title order={1} mb="xs">
        Spatial ML
      </Title>
      <Text c="dimmed" mb="xl">
        Tools for creating training datasets from PDF maps and converting them to GeoJSON.
      </Text>

      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
        {FEATURES.map((feature) =>
          feature.disabled ? (
            <Card
              key={feature.title}
              shadow="sm"
              padding="lg"
              radius="md"
              withBorder
              style={{ cursor: "not-allowed", opacity: 0.6 }}
            >
              <Group mb="md">
                <ThemeIcon size="lg" variant="light">
                  <feature.icon size={20} />
                </ThemeIcon>
                <Text fw={500}>{feature.title}</Text>
              </Group>
              <Text size="sm" c="dimmed">
                {feature.description}
              </Text>
              <Text size="xs" c="dimmed" mt="sm">
                Coming soon
              </Text>
            </Card>
          ) : (
            <Card
              key={feature.title}
              shadow="sm"
              padding="lg"
              radius="md"
              withBorder
              component={Link}
              href={feature.href}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <Group mb="md">
                <ThemeIcon size="lg" variant="light">
                  <feature.icon size={20} />
                </ThemeIcon>
                <Text fw={500}>{feature.title}</Text>
              </Group>
              <Text size="sm" c="dimmed">
                {feature.description}
              </Text>
            </Card>
          )
        )}
      </SimpleGrid>
    </Container>
  );
}
