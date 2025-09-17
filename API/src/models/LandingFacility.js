import mongoose from "mongoose";

const LandingFacilitySchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    type: { type: String, enum: ["helipad", "airstrip"], required: true },
    category: { type: String, enum: ["private", "commercial"], required: true },
    location: {
      type: { type: String, enum: ["Point"], default: "Point" },
      coordinates: { type: [Number], required: true } // [lon, lat]
    },
    landing_capacity: {
      jets: { type: Boolean, required: true },
      choppers: { type: Boolean, required: true },
      max_weight_tons: { type: Number, required: true }
    },
    booking_status: {
      available: { type: Boolean, required: true },
      next_available_time: { type: Date, default: null }
    },
    reference_info: {
      source: { type: String, enum: ["airble", "jetsetgo", "local_database"], required: true },
      url: { type: String, default: null }
    }
  },
  { timestamps: true }
);

// 2dsphere for $geoNear
LandingFacilitySchema.index({ location: "2dsphere" });

export const LandingFacility = mongoose.model("LandingFacility", LandingFacilitySchema);
