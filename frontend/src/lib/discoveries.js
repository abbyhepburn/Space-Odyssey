import objects from '../../../shared/discoveries.json' with {type:'json'};
export const SCENE_ANCHORS = Object.freeze({EARTH:[-55,14,-200], JUPITER:[110,14,-200], SATURN:[0,14,-220], MERCURY:[-205,14,-100], VENUS:[-175,14,-165], NEPTUNE:[200,14,-160]});
export const discoveries = objects;
export const isDeepSky = d => d.zone==='DEEP_SKY';
