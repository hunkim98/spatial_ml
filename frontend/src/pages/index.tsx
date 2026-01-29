import { useState } from "react";
import Head from "next/head";
import {
  Container,
  Title,
  Text,
  Button,
  Group,
  Stack,
  SimpleGrid,
  Card,
  ThemeIcon,
  Box,
  Badge,
  Anchor,
  Divider,
  Modal,
  Image,
} from "@mantine/core";
import {
  IconMap,
  IconFileTypePdf,
  IconTransform,
  IconBuildingCommunity,
  IconArrowRight,
  IconMail,
  IconCheck,
  IconMapPin,
} from "@tabler/icons-react";
import type { ReactElement } from "react";
import dynamic from "next/dynamic";
import { EditorProvider } from "@/canvas/context";
import { GeoCorners } from "@/canvas/types";

// Dynamic import to avoid SSR issues with MapLibre
const GeoReferencer = dynamic(
  () => import("@/components/GeoReferencer").then((mod) => mod.GeoReferencer),
  { ssr: false }
);

// Anniston, AL demo configuration
const ANNISTON_CENTER = { lng: -85.843, lat: 33.676 };
const ANNISTON_PDF_URL = "/2024-Zoning-Map.pdf";
const ANNISTON_CORNERS: GeoCorners = {
  topLeft: { lng: -85.934926, lat: 33.753125 },
  topRight: { lng: -85.751109, lat: 33.753125 },
  bottomRight: { lng: -85.751109, lat: 33.600156 },
  bottomLeft: { lng: -85.934926, lat: 33.600156 },
};

const FEATURES = [
  {
    icon: IconFileTypePdf,
    title: "Upload PDF Maps",
    description:
      "Start with any zoning map PDF or scanned document. Our tool handles the complexity of legacy formats.",
  },
  {
    icon: IconMapPin,
    title: "Georeference with Ease",
    description:
      "Align your PDF directly onto satellite imagery with our intuitive web-based editor. No GIS expertise required.",
  },
  {
    icon: IconTransform,
    title: "Convert to GeoJSON",
    description:
      "Automatically extract zoning polygons and export them as industry-standard GeoJSON files.",
  },
  {
    icon: IconBuildingCommunity,
    title: "Serve Your Community",
    description:
      "Publish interactive zoning maps that residents and developers can actually use.",
  },
];

const PROBLEM_IMAGES = [
  "/problem/suttons_bay.png",
  "/problem/bingham_township.png",
  "/problem/empire_township.png",
];

const DIFFERENTIATORS = [
  "Creates GIS zoning data where none exists",
  "Built for municipalities without GIS capacity",
  "Free for governments to digitize maps",
  "Expands zoning coverage into unmapped regions",
];

const CONTACT_EMAIL = "donghun_kim@mde.harvard.edu";

function Home() {
  const [modalOpened, setModalOpened] = useState(false);

  return (
    <Box>
      <Head>
        <title>Spatially - Convert Zoning PDFs to Digital GIS Maps</title>
        <meta
          name="description"
          content="Free web-based tool that converts zoning map PDFs into GIS data. Built for municipalities without GIS capacity. Transform paper maps into interactive digital maps."
        />
        <meta name="keywords" content="zoning maps, GIS, georeference, PDF to GIS, urban planning, municipality, digital maps, geospatial" />

        {/* Open Graph / Facebook */}
        <meta property="og:type" content="website" />
        <meta property="og:title" content="Spatially - Convert Zoning PDFs to Digital GIS Maps" />
        <meta
          property="og:description"
          content="Free web-based tool that converts zoning map PDFs into GIS data. Built for municipalities without GIS capacity."
        />
        <meta property="og:image" content="/icon.png" />

        {/* Twitter */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="Spatially - Convert Zoning PDFs to Digital GIS Maps" />
        <meta
          name="twitter:description"
          content="Free web-based tool that converts zoning map PDFs into GIS data. Built for municipalities without GIS capacity."
        />
        <meta name="twitter:image" content="/icon.png" />

        {/* Additional SEO */}
        <meta name="robots" content="index, follow" />
        <meta name="author" content="Spatially" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Coming Soon Modal */}
      <Modal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title="Editor Coming Soon"
        centered
        size="md"
      >
        <Stack gap="md">
          <Text>
            Our georeference editor is currently in development. We are focused on
            collecting training data to build accurate PDF-to-GIS conversion models.
          </Text>
          <Text c="dimmed" size="sm">
            Want early access or to participate in our pilot program? Reach out to us
            at <Anchor href="mailto:donghun_kim@mde.harvard.edu">donghun_kim@mde.harvard.edu</Anchor>
          </Text>
          <Button
            variant="gradient"
            gradient={{ from: "cyan", to: "teal" }}
            onClick={() => setModalOpened(false)}
          >
            Got it
          </Button>
        </Stack>
      </Modal>

      {/* Hero Section */}
      <Box
        style={{
          background: "linear-gradient(135deg, #1a1b1e 0%, #25262b 50%, #1a1b1e 100%)",
          borderBottom: "1px solid #373A40",
        }}
      >
        <Container size="lg" py={{ base: 48, sm: 80 }}>
          <Stack align="center" gap="lg">
            {/* Logo */}
            <img
              src="/icon.png"
              alt="Spatially Logo"
              style={{ width: 72, height: 72 }}
            />

            <Title
              order={1}
              ta="center"
              fz={{ base: 36, sm: 48, md: 56 }}
              fw={700}
              lts={-1}
              c="white"
            >
              Spatially
            </Title>

            <Text size="lg" c="dimmed" ta="center" maw={600} px="md">
              Lowering the Barrier to GIS for Urban Planning
            </Text>

            <Text size="md" c="gray.4" ta="center" maw={700} lh={1.7} px="md">
              We build tools that turn zoning PDFs and hand-drawn maps into usable
              digital maps, creating an on-ramp to everyday GIS use for planning
              boards with limited capacity.
            </Text>

            <Group mt="md">
              <Button
                size="lg"
                variant="gradient"
                gradient={{ from: "cyan", to: "teal" }}
                rightSection={<IconArrowRight size={18} />}
                onClick={() => setModalOpened(true)}
              >
                Try the Tool
              </Button>
            </Group>
          </Stack>
        </Container>
      </Box>

      {/* Problem Section */}
      <Box py={80} bg="dark.7" style={{ borderTop: "1px solid #373A40" }}>
        <Container size="lg">
          <Stack align="center" gap="xl" mb={60}>
            <Badge variant="light" color="red" size="lg">
              The Problem
            </Badge>
            <Title order={2} c="white" ta="center">
              Planning decisions still depend on PDFs and paper maps
            </Title>

            {/* Stats integrated into problem section */}
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg" w="100%" maw={800}>
              <Box ta="center">
                <Text style={{ fontSize: 36, fontWeight: 700, lineHeight: 1.1 }} c="red.4">
                  ~40%
                </Text>
                <Text size="sm" c="dimmed" mt={4}>
                  of U.S. municipalities lack digital zoning maps
                </Text>
              </Box>
              <Box ta="center">
                <Text style={{ fontSize: 36, fontWeight: 700, lineHeight: 1.1 }} c="orange.4">
                  19,000+
                </Text>
                <Text size="sm" c="dimmed" mt={4}>
                  municipalities across the United States
                </Text>
              </Box>
              <Box ta="center">
                <Text style={{ fontSize: 36, fontWeight: 700, lineHeight: 1.1 }} c="yellow.4">
                  $700+
                </Text>
                <Text size="sm" c="dimmed" mt={4}>
                  per user/year for enterprise GIS software
                </Text>
              </Box>
            </SimpleGrid>

            <Text c="gray.4" ta="center" maw={700} lh={1.8}>
              Many municipalities rely solely on PDFs or scanned, hand-marked
              documents that are difficult to work with.
            </Text>
          </Stack>

          {/* Infinite Carousel of Problem Images */}
          <Box
            mb={60}
            style={{
              overflow: "hidden",
              maskImage: "linear-gradient(to right, transparent, black 10%, black 90%, transparent)",
              WebkitMaskImage: "linear-gradient(to right, transparent, black 10%, black 90%, transparent)",
            }}
          >
            <Box
              style={{
                display: "flex",
                gap: 24,
                animation: "scroll 20s linear infinite",
                width: "fit-content",
              }}
            >
              {/* Duplicate images for seamless loop */}
              {[...PROBLEM_IMAGES, ...PROBLEM_IMAGES, ...PROBLEM_IMAGES].map((image, index) => (
                <Box
                  key={index}
                  style={{
                    flexShrink: 0,
                    borderRadius: 12,
                    overflow: "hidden",
                    border: "1px solid #373A40",
                  }}
                >
                  <Image
                    src={image}
                    alt="Zoning map example"
                    h={200}
                    w={300}
                    fit="cover"
                  />
                </Box>
              ))}
            </Box>
            <style>{`
              @keyframes scroll {
                0% { transform: translateX(0); }
                100% { transform: translateX(calc(-324px * ${PROBLEM_IMAGES.length})); }
              }
            `}</style>
          </Box>

          {/* Why is this hard */}
          <Text c="gray.5" ta="center" mb="lg" fw={500}>
            Why does this happen?
          </Text>
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
            <Card bg="dark.6" p="lg" radius="md">
              <Group wrap="nowrap" align="flex-start">
                <ThemeIcon color="red" variant="light" size="lg" style={{ flexShrink: 0 }}>
                  <IconBuildingCommunity size={20} />
                </ThemeIcon>
                <Box>
                  <Text fw={500} c="white" size="sm">
                    Limited Budgets
                  </Text>
                  <Text size="xs" c="dimmed">
                    Small planning boards cannot afford enterprise GIS licenses
                  </Text>
                </Box>
              </Group>
            </Card>
            <Card bg="dark.6" p="lg" radius="md">
              <Group wrap="nowrap" align="flex-start">
                <ThemeIcon color="orange" variant="light" size="lg" style={{ flexShrink: 0 }}>
                  <IconMap size={20} />
                </ThemeIcon>
                <Box>
                  <Text fw={500} c="white" size="sm">
                    Technical Complexity
                  </Text>
                  <Text size="xs" c="dimmed">
                    Digitizing maps requires manually tracing boundaries
                  </Text>
                </Box>
              </Group>
            </Card>
            <Card bg="dark.6" p="lg" radius="md">
              <Group wrap="nowrap" align="flex-start">
                <ThemeIcon color="yellow" variant="light" size="lg" style={{ flexShrink: 0 }}>
                  <IconFileTypePdf size={20} />
                </ThemeIcon>
                <Box>
                  <Text fw={500} c="white" size="sm">
                    Understaffed Teams
                  </Text>
                  <Text size="xs" c="dimmed">
                    No dedicated GIS staff to maintain digital maps
                  </Text>
                </Box>
              </Group>
            </Card>
          </SimpleGrid>
        </Container>
      </Box>

      {/* Solution Section */}
      <Box py={80} bg="dark.8">
        <Container size="lg">
          <Stack align="center" gap="xl" mb={60}>
            <Badge variant="light" color="cyan" size="lg">
              Our Solution
            </Badge>
            <Title order={2} c="white" ta="center">
              From PDF to Interactive Map in Minutes
            </Title>
            <Text c="gray.4" ta="center" maw={600}>
              Our web-based editor makes it easy to georeference zoning PDFs and
              convert them to usable GIS data—no specialized software required.
            </Text>
          </Stack>

          <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
            {FEATURES.map((feature, index) => (
              <Card
                key={feature.title}
                bg="dark.6"
                p="xl"
                radius="md"
                style={{ border: "1px solid #373A40" }}
              >
                <Stack gap="md">
                  <Group>
                    <ThemeIcon
                      size={48}
                      radius="md"
                      variant="gradient"
                      gradient={{ from: "cyan", to: "teal" }}
                    >
                      <feature.icon size={24} />
                    </ThemeIcon>
                    <Badge variant="light" color="gray" size="sm">
                      Step {index + 1}
                    </Badge>
                  </Group>
                  <Text fw={600} c="white">
                    {feature.title}
                  </Text>
                  <Text size="sm" c="dimmed" lh={1.6}>
                    {feature.description}
                  </Text>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        </Container>
      </Box>

      {/* Demo Preview Section */}
      <Box py={80} bg="dark.7">
        <Container size="lg">
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing={60}>
            <Stack gap="lg" justify="center">
              <Badge variant="light" color="green" size="lg">
                See It In Action
              </Badge>
              <Title order={2} c="white">
                Digitize Zoning Maps with Ease
              </Title>
              <Text c="gray.4" lh={1.8}>
                Our tool helps urban planners convert static PDF maps into
                usable GIS polygons. Upload your zoning map, align it to
                real-world coordinates, and generate digital boundaries ready
                for any GIS platform.
              </Text>
              <Stack gap="xs">
                {[
                  "Upload any zoning PDF or scanned map",
                  "Align to satellite imagery with built-in georeferencing",
                  "Generate zoning polygons as GeoJSON",
                  "AI-assisted boundary detection (coming soon)",
                ].map((item) => (
                  <Group key={item} gap="sm">
                    <ThemeIcon color="green" variant="light" size="sm">
                      <IconCheck size={14} />
                    </ThemeIcon>
                    <Text size="sm" c="gray.4">
                      {item}
                    </Text>
                  </Group>
                ))}
              </Stack>
              <Group mt="md">
                <Button
                  variant="gradient"
                  gradient={{ from: "cyan", to: "teal" }}
                  rightSection={<IconArrowRight size={16} />}
                  onClick={() => setModalOpened(true)}
                >
                  Try the Tool
                </Button>
              </Group>
            </Stack>
            <Box
              h={{ base: 350, sm: 400, md: 450 }}
              style={{
                background: "#1a1b1e",
                borderRadius: 16,
                overflow: "hidden",
                border: "1px solid #373A40",
                position: "relative",
              }}
            >
              <EditorProvider>
                <GeoReferencer
                  pdfUrl={ANNISTON_PDF_URL}
                  initialCenter={ANNISTON_CENTER}
                  initialZoom={11}
                  initialCorners={ANNISTON_CORNERS}
                  readOnly={true}
                />
              </EditorProvider>
              <Box
                style={{
                  position: "absolute",
                  bottom: 16,
                  left: 16,
                  right: 16,
                  background: "rgba(0,0,0,0.8)",
                  borderRadius: 8,
                  padding: "12px 16px",
                  pointerEvents: "none",
                }}
              >
                <Text size="sm" c="white">
                  Anniston, AL - Zoning map aligned with satellite imagery
                </Text>
              </Box>
            </Box>
          </SimpleGrid>
        </Container>
      </Box>

      {/* Differentiators Section */}
      <Box py={80} bg="dark.8">
        <Container size="md">
          <Stack align="center" gap="xl">
            <Badge variant="light" color="violet" size="lg">
              Why Spatially?
            </Badge>
            <Title order={2} c="white" ta="center">
              Built Different
            </Title>
            <Text c="gray.4" ta="center" maw={500}>
              While competitors focus on cities that already have digital maps,
              we create GIS data where none exists.
            </Text>
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg" mt="xl">
              {DIFFERENTIATORS.map((item) => (
                <Card key={item} bg="dark.6" p="lg" radius="md">
                  <Group>
                    <ThemeIcon
                      color="violet"
                      variant="light"
                      size="lg"
                      radius="xl"
                    >
                      <IconCheck size={18} />
                    </ThemeIcon>
                    <Text c="white" fw={500}>
                      {item}
                    </Text>
                  </Group>
                </Card>
              ))}
            </SimpleGrid>
          </Stack>
        </Container>
      </Box>

      {/* Contact Section */}
      <Box py={80} bg="dark.7">
        <Container size="sm">
          <Stack align="center" gap="xl">
            <ThemeIcon
              size={64}
              radius="xl"
              variant="gradient"
              gradient={{ from: "cyan", to: "teal" }}
            >
              <IconMail size={32} />
            </ThemeIcon>
            <Title order={2} c="white" ta="center">
              Are you an urban planner?
            </Title>
            <Text c="gray.4" ta="center" maw={500} lh={1.8}>
              We&apos;re looking for municipalities interested in trying out our
              georeference tool. If you work with zoning maps and want to help
              us build better tools, we&apos;d love to hear from you.
            </Text>

            <Button
              size="lg"
              variant="gradient"
              gradient={{ from: "cyan", to: "teal" }}
              leftSection={<IconMail size={20} />}
              component="a"
              href={`mailto:${CONTACT_EMAIL}?subject=Interest in Spatially`}
            >
              Get in Touch
            </Button>
          </Stack>
        </Container>
      </Box>

      {/* Footer */}
      <Box py={40} bg="dark.9" style={{ borderTop: "1px solid #373A40" }}>
        <Container size="lg">
          <Group justify="space-between" align="center">
            <Group gap="md">
              <ThemeIcon
                size="md"
                variant="gradient"
                gradient={{ from: "cyan", to: "teal" }}
              >
                <IconMapPin size={16} />
              </ThemeIcon>
              <Text fw={600} c="white">
                Spatially
              </Text>
            </Group>
            <Group gap="md">
              <Anchor href="mailto:donghun_kim@mde.harvard.edu" c="dimmed" size="sm">
                <Group gap={4}>
                  <IconMail size={16} />
                  Contact
                </Group>
              </Anchor>
            </Group>
          </Group>
          <Divider my="lg" color="dark.6" />
          <Text size="xs" c="dimmed" ta="center">
            Harvard President&apos;s Innovation Challenge 2026
          </Text>
        </Container>
      </Box>
    </Box>
  );
}

// Use custom layout (no header) for landing page
Home.getLayout = function getLayout(page: ReactElement) {
  return page;
};

export default Home;
