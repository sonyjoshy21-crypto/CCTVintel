import math

class SimpleTracker:
    def __init__(self, max_distance=100, max_disappeared=10):
        self.next_object_id = 0
        self.objects = {}
        self.max_distance = max_distance
        self.max_disappeared = max_disappeared

    def register(self, detection, frame_count):
        self.objects[self.next_object_id] = {
            "bbox": detection["bbox"],
            "class": detection["class"],
            "confidence": detection["confidence"],
            "centroids": [self._get_centroid(detection["bbox"])],
            "frame_counts": [frame_count],
            "disappeared": 0,
            "speed": 0,
            "action": "unknown"
        }
        self.next_object_id += 1

    def deregister(self, object_id):
        del self.objects[object_id]

    def _get_centroid(self, bbox):
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)

    def _calculate_distance(self, c1, c2):
        return math.hypot(c1[0] - c2[0], c1[1] - c2[1])

    def update(self, detections, frame_count):
        if len(self.objects) == 0:
            for det in detections:
                self.register(det, frame_count)
        else:
            object_ids = list(self.objects.keys())
            object_centroids = [self.objects[oid]["centroids"][-1] for oid in object_ids]
            
            input_centroids = [self._get_centroid(det["bbox"]) for det in detections]
            
            used_objects = set()
            used_inputs = set()
            
            for i, inp_c in enumerate(input_centroids):
                best_dist = float('inf')
                best_oid = None
                
                for j, oid in enumerate(object_ids):
                    if oid in used_objects: continue
                    dist = self._calculate_distance(inp_c, object_centroids[j])
                    if dist < best_dist and dist < self.max_distance:
                        best_dist = dist
                        best_oid = oid
                        
                if best_oid is not None:
                    obj = self.objects[best_oid]
                    obj["centroids"].append(inp_c)
                    obj["frame_counts"].append(frame_count)
                    obj["bbox"] = detections[i]["bbox"]
                    obj["disappeared"] = 0
                    
                    if len(obj["centroids"]) > 1:
                        dist = self._calculate_distance(obj["centroids"][-1], obj["centroids"][-2])
                        frames_elapsed = obj["frame_counts"][-1] - obj["frame_counts"][-2]
                        if frames_elapsed > 0:
                            obj["speed"] = dist / frames_elapsed
                        
                        if obj["speed"] > 10:
                            obj["action"] = "running"
                        elif obj["speed"] > 2:
                            obj["action"] = "walking" if obj["class"] == "person" else "driving"
                        else:
                            obj["action"] = "standing" if obj["class"] == "person" else "parked"
                    
                    used_objects.add(best_oid)
                    used_inputs.add(i)
                else:
                    self.register(detections[i], frame_count)
                    
            for oid in list(self.objects.keys()):
                if oid not in used_objects:
                    self.objects[oid]["disappeared"] += 1
                    
                    if self.objects[oid]["disappeared"] > 30 and self.objects[oid]["class"] != "person":
                        self.objects[oid]["action"] = "abandoned"
                        
                    if self.objects[oid]["disappeared"] > self.max_disappeared:
                        self.deregister(oid)
                        
        results = []
        for oid, obj in self.objects.items():
            if obj["disappeared"] == 0:
                results.append({
                    "track_id": oid,
                    "bbox": obj["bbox"],
                    "class": obj["class"],
                    "confidence": obj["confidence"],
                    "speed": obj["speed"],
                    "action": obj["action"]
                })
        return results
