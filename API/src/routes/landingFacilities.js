import express from "express";
import { LandingFacility } from "../models/LandingFacility.js";
import { parseNearbyQuery } from "../utils/validation.js";

const router = express.Router();

/**
 * GET /api/landing-facilities/nearby
 * Query: lat, lon, radius_km (default 20), facility_type (helipad|airstrip|both, default both)
 * Response: matches the spec
 */
router.get("/nearby", async (req, res) => {
  const { lat, lon, radiusKm, facilityType, errors } = parseNearbyQuery(req.query);

  if (errors.length) {
    return res.status(400).json({ errors });
  }

  try {
    // Build type filter
    const typeFilter =
      facilityType === "both"
        ? {}
        : { type: facilityType };

    // $geoNear returns distance in meters
    const pipeline = [
      {
        $geoNear: {
          near: { type: "Point", coordinates: [lon, lat] },
          distanceField: "distance_m",
          spherical: true,
          maxDistance: radiusKm * 1000
        }
      },
      { $match: typeFilter },
      // Optional: project only needed fields and compute distance_km
      {
        $project: {
          name: 1,
          type: 1,
          category: 1,
          location: 1,
          landing_capacity: 1,
          booking_status: 1,
          reference_info: 1,
          distance_km: { $divide: ["$distance_m", 1000] }
        }
      },
      { $sort: { distance_km: 1 } }
    ];

    const docs = await LandingFacility.aggregate(pipeline);

    const available_facilities = docs.map((d) => ({
      id: String(d._id),
      name: d.name,
      type: d.type,
      category: d.category,
      latitude: d.location.coordinates[1],
      longitude: d.location.coordinates[0],
      distance_km: Number(d.distance_km.toFixed(2)),
      landing_capacity: {
        jets: d.landing_capacity.jets,
        choppers: d.landing_capacity.choppers,
        max_weight_tons: d.landing_capacity.max_weight_tons
      },
      booking_status: {
        available: d.booking_status.available,
        next_available_time: d.booking_status.next_available_time
          ? d.booking_status.next_available_time.toISOString()
          : null
      },
      reference_info: {
        source: d.reference_info.source,
        url: d.reference_info.url || null
      }
    }));

    return res.json({
      available_facilities,
      metadata: {
        query_lat: lat,
        query_lon: lon,
        radius_km: radiusKm,
        returned_count: available_facilities.length
      }
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: "Internal server error" });
  }
});

export default router;
