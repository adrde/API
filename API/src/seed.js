import dotenv from "dotenv";
import { connectDB } from "./db.js";
import { LandingFacility } from "./models/LandingFacility.js";

dotenv.config();

function mockAvailability(name) {
  // Deterministic "mock": names with even length available, else next slot in 2h
  const available = name.length % 2 === 0;
  return {
    available,
    next_available_time: available ? null : new Date(Date.now() + 2 * 60 * 60 * 1000)
  };
}

async function run() {
  await connectDB();

  await LandingFacility.deleteMany({});

  const seed = [
    // Around Jaipur (26.9124, 75.7873)
    {
      name: "Rajasthan Private Helipad",
      type: "helipad",
      category: "private",
      location: { type: "Point", coordinates: [75.790, 26.915] },
      landing_capacity: { jets: false, choppers: true, max_weight_tons: 5 },
      booking_status: mockAvailability("Rajasthan Private Helipad"),
      reference_info: { source: "local_database", url: null }
    },
    {
      name: "Nearby Commercial Airstrip",
      type: "airstrip",
      category: "commercial",
      location: { type: "Point", coordinates: [75.820, 26.950] },
      landing_capacity: { jets: true, choppers: true, max_weight_tons: 50 },
      booking_status: mockAvailability("Nearby Commercial Airstrip"),
      reference_info: { source: "jetsetgo", url: "https://jetsetgo.in/sample-facility" }
    },
    // A few more varied points
    {
      name: "City Hospital Helipad",
      type: "helipad",
      category: "commercial",
      location: { type: "Point", coordinates: [75.805, 26.905] },
      landing_capacity: { jets: false, choppers: true, max_weight_tons: 4 },
      booking_status: mockAvailability("City Hospital Helipad"),
      reference_info: { source: "airble", url: null }
    },
    {
      name: "Desert Edge Airstrip",
      type: "airstrip",
      category: "private",
      location: { type: "Point", coordinates: [75.700, 26.880] },
      landing_capacity: { jets: true, choppers: true, max_weight_tons: 60 },
      booking_status: mockAvailability("Desert Edge Airstrip"),
      reference_info: { source: "local_database", url: null }
    }
  ];

  await LandingFacility.insertMany(seed);
  console.log(`🌱 Seeded ${seed.length} facilities`);
  process.exit(0);
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
