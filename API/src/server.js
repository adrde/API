import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { connectDB } from "./db.js";
import landingFacilitiesRouter from "./routes/landingFacilities.js";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

// Healthcheck
app.get("/health", (req, res) => res.json({ status: "ok" }));

// API routes
app.use("/api/landing-facilities", landingFacilitiesRouter);

const PORT = process.env.PORT || 3000;

(async () => {
  try {
    await connectDB();
    app.listen(PORT, () => {
      console.log(` API running at http://localhost:${PORT}`);
    });
  } catch (err) {
    console.error("Failed to start:", err);
    process.exit(1);
  }
})();
