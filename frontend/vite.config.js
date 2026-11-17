import { defineConfig } from "vite";

export default defineConfig({
  optimizeDeps: {
    entries: ["src/main.jsx"],
    include: ["react", "react-dom/client", "react-router-dom", "axios", "lucide-react", "recharts"],
  },
  server: {
    host: "127.0.0.1",
    fs: { strict: true },
  },
});
