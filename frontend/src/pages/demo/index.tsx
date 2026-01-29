import {
  Container,
  Title,
  Text,
  Card,
  Group,
  Button,
  ThemeIcon,
  Stepper,
  SimpleGrid,
  Paper,
  Box,
} from "@mantine/core";
import {
  IconUpload,
  IconMap,
  IconPolygon,
  IconEdit,
  IconDownload,
  IconEye,
  IconCheck,
} from "@tabler/icons-react";
import Link from "next/link";
import { Layout } from "@/components/Layout";
import { WORKFLOW_STEPS, ZONE_TYPES, ANNISTON_CENTER } from "@/data/anniston-demo";

const STEP_ICONS = [IconUpload, IconMap, IconPolygon, IconEdit, IconDownload];

export default function DemoPage() {
  // Find current step
  const currentStepIndex = WORKFLOW_STEPS.findIndex((s) => s.status === "current");

  return (
    <Layout>
      <Container size="lg" py="xl">
        {/* Header */}
        <Group justify="space-between" mb="xl">
          <div>
            <Title order={1}>Anniston, AL</Title>
            <Text c="dimmed" mt="xs">
              Zoning map digitization project
            </Text>
          </div>
        </Group>

        {/* Workflow Progress */}
        <Card shadow="sm" padding="lg" radius="md" withBorder mb="xl">
          <Title order={4} mb="md">
            Workflow Progress
          </Title>
          <Stepper active={currentStepIndex} size="sm">
            {WORKFLOW_STEPS.map((step, index) => {
              const Icon = STEP_ICONS[index];
              return (
                <Stepper.Step
                  key={step.step}
                  label={step.title}
                  description={step.description}
                  icon={<Icon size={18} />}
                  completedIcon={<IconCheck size={18} />}
                />
              );
            })}
          </Stepper>
        </Card>

        {/* Main Actions */}
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg" mb="xl">
          {/* Georeferencer Card */}
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group mb="md">
              <ThemeIcon size="lg" variant="light" color="blue">
                <IconMap size={20} />
              </ThemeIcon>
              <div>
                <Text fw={500}>Georeference</Text>
                <Text size="xs" c="dimmed">
                  Align PDF with imagery
                </Text>
              </div>
            </Group>
            <Text size="sm" c="dimmed" mb="md">
              Position the zoning map PDF on the satellite view to establish geographic coordinates.
            </Text>
            <Button
              component={Link}
              href="/labeller"
              variant="light"
              fullWidth
              leftSection={<IconMap size={16} />}
            >
              Open
            </Button>
          </Card>

          {/* Polygons Card */}
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group mb="md">
              <ThemeIcon size="lg" variant="light" color="cyan">
                <IconPolygon size={20} />
              </ThemeIcon>
              <div>
                <Text fw={500}>Extracted Polygons</Text>
                <Text size="xs" c="dimmed">
                  Raw polygon boundaries
                </Text>
              </div>
            </Group>
            <Text size="sm" c="dimmed" mb="md">
              View the extracted polygon boundaries before zone classification is applied.
            </Text>
            <Button
              component={Link}
              href="/demo/polygons"
              variant="light"
              color="cyan"
              fullWidth
              leftSection={<IconPolygon size={16} />}
            >
              Open
            </Button>
          </Card>

          {/* Labeled Viewer Card */}
          <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Group mb="md">
              <ThemeIcon size="lg" variant="light" color="green">
                <IconEye size={20} />
              </ThemeIcon>
              <div>
                <Text fw={500}>Labeled Zones</Text>
                <Text size="xs" c="dimmed">
                  With zone classification
                </Text>
              </div>
            </Group>
            <Text size="sm" c="dimmed" mb="md">
              View polygons with zone types assigned. Click parcels to see zoning details.
            </Text>
            <Button
              component={Link}
              href="/demo/viewer"
              variant="light"
              color="green"
              fullWidth
              leftSection={<IconEye size={16} />}
            >
              Open
            </Button>
          </Card>
        </SimpleGrid>

        {/* Zone Types Legend */}
        <Card shadow="sm" padding="lg" radius="md" withBorder>
          <Title order={4} mb="md">
            Anniston Zoning Districts
          </Title>
          <Text size="sm" c="dimmed" mb="lg">
            The city uses a form-based zoning code with {Object.keys(ZONE_TYPES).length} district types.
          </Text>
          <SimpleGrid cols={{ base: 2, sm: 3, md: 4 }} spacing="sm">
            {Object.values(ZONE_TYPES).map((zone) => (
              <Paper key={zone.code} p="xs" withBorder>
                <Group gap="xs">
                  <Box
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: 4,
                      backgroundColor: zone.color,
                    }}
                  />
                  <div>
                    <Text size="sm" fw={500}>
                      {zone.code}
                    </Text>
                    <Text size="xs" c="dimmed" lineClamp={1}>
                      {zone.name}
                    </Text>
                  </div>
                </Group>
              </Paper>
            ))}
          </SimpleGrid>
        </Card>

        {/* City Info */}
        <Card shadow="sm" padding="lg" radius="md" withBorder mt="xl">
          <Title order={4} mb="md">
            About Anniston, AL
          </Title>
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
            <div>
              <Text size="xs" c="dimmed" tt="uppercase">
                Location
              </Text>
              <Text fw={500}>
                {ANNISTON_CENTER.lat.toFixed(4)}°N, {Math.abs(ANNISTON_CENTER.lng).toFixed(4)}°W
              </Text>
            </div>
            <div>
              <Text size="xs" c="dimmed" tt="uppercase">
                Zoning Document
              </Text>
              <Text fw={500}>2024-Zoning-Map.pdf</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed" tt="uppercase">
                District Types
              </Text>
              <Text fw={500}>{Object.keys(ZONE_TYPES).length} zones</Text>
            </div>
          </SimpleGrid>
        </Card>
      </Container>
    </Layout>
  );
}
