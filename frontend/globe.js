// globe.js
import * as THREE from 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.module.js';

const EARTH_RADIUS = 6371;
const SCALE = 1 / 1000;

let scene, camera, renderer, earthGroup;
let isDragging = false;
let prevMouse = { x: 0, y: 0 };
let satPoints, debrisPoints;

export function initGlobe() {
    const container = document.getElementById('globe-container');

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 25);

    renderer = new THREE.WebGLRenderer({
        canvas: document.getElementById('globe-canvas'),
        antialias: true,
        alpha: true
    });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    earthGroup = new THREE.Group();
    scene.add(earthGroup);

    const geo = new THREE.SphereGeometry(EARTH_RADIUS * SCALE, 64, 64);
    earthGroup.add(new THREE.Mesh(geo, new THREE.MeshPhongMaterial({
        color: 0x1a1a2e,
        emissive: 0x0a0a1a,
    })));

    earthGroup.add(new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
        color: 0x00f5ff,
        wireframe: true,
        transparent: true,
        opacity: 0.08,
    })));

    scene.add(new THREE.AmbientLight(0x444444));
    const sun = new THREE.DirectionalLight(0xffffff, 1);
    sun.position.set(5, 3, 5);
    scene.add(sun);

    const canvas = renderer.domElement;
    canvas.addEventListener('mousedown', e => {
        isDragging = true;
        prevMouse = { x: e.clientX, y: e.clientY };
    });
    canvas.addEventListener('mouseup', () => isDragging = false);
    canvas.addEventListener('mouseleave', () => isDragging = false);
    canvas.addEventListener('mousemove', e => {
        if (!isDragging) return;
        earthGroup.rotation.y += (e.clientX - prevMouse.x) * 0.005;
        earthGroup.rotation.x += (e.clientY - prevMouse.y) * 0.005;
        prevMouse = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener('wheel', e => {
        camera.position.z = Math.max(10, Math.min(60, camera.position.z + e.deltaY * 0.02));
    }, { passive: true });

    window.addEventListener('resize', () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });

    animate();
}


function eciToVec3(x, y, z) {
    return new THREE.Vector3(x * SCALE, z * SCALE, -y * SCALE);
}


export function updateSatellites(data) {
    if (!data || !data.length) return;

    if (satPoints) {
        satPoints.geometry.dispose();
        satPoints.material.dispose();
        earthGroup.remove(satPoints);
    }
    const positions = [];
    data.forEach(d => {
        const v = eciToVec3(d.x, d.y, d.z);
        positions.push(v.x, v.y, v.z);
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    satPoints = new THREE.Points(geo, new THREE.PointsMaterial({
        color: 0x00f5ff, size: 0.08, sizeAttenuation: true,
    }));
    earthGroup.add(satPoints);
}


export function updateDebris(data) {
    if (!data || !data.length) return;

    if (debrisPoints) {
        debrisPoints.geometry.dispose();
        debrisPoints.material.dispose();
        earthGroup.remove(debrisPoints);
    }
    const positions = [];
    data.forEach(d => {
        const v = eciToVec3(d.x, d.y, d.z);
        positions.push(v.x, v.y, v.z);
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    debrisPoints = new THREE.Points(geo, new THREE.PointsMaterial({
        color: 0xff4444, size: 0.05, sizeAttenuation: true,
    }));
    earthGroup.add(debrisPoints);
}


function animate() {
    requestAnimationFrame(animate);
    if (!isDragging) earthGroup.rotation.y += 0.000072722 / 60;
    renderer.render(scene, camera);
}
