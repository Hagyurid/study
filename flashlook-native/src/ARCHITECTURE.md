# V5 memory architecture

1. Pick a photo.
2. Call `analyzePhotoOnce()` exactly once.
3. Native depth backend returns an 8-bit depth map.
4. Immediately derive 8-bit flash/specular response maps.
5. Release the inference session/model.
6. Editor keeps only photo URI + compact maps.
7. Slider movement never calls depth inference.

The current depth-engine contains a neutral synthetic depth fallback so the cache lifecycle can be developed and tested without accidentally reintroducing the browser Transformers.js path.

The next required binary asset is a Core ML depth model compatible with the selected native module. Do not commit a guessed model or claim real depth inference until that asset/backend is integrated and device-tested.
