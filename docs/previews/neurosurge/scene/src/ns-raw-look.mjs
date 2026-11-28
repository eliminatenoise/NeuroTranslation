































































export const RAW_LOOK = Object.freeze({
  on: true,
  light: Object.freeze([0.4, 0.6, 0.7]),
  ambient: 0.25, direct: 0.75, back: 0.6, gamma: 2.2,
  flat: false,
  room: Object.freeze([0.0011, 0.0011, 0.0015]), roomPool: Object.freeze([0.0045, 0.0048, 0.0056]),
  bone: 0xe8e0cd, muscleFloor: 0.01, muscleFloorKeep: 1, muscleFloorRef: 0.0621,
  ink: Object.freeze({ colour: Object.freeze([0x0b / 255, 0x08 / 255, 0x09 / 255]), hex: 0x0b0809, css: 1.4, alpha: 0.95, innerCss: 0.9, innerAlpha: 0.6, farShare: 0.6 })
});

const f = v => (Number.isInteger(v) ? v.toFixed(1) : String(v));

/** The light's unit direction (view space). Pure. */
export function rawLightDir(o = RAW_LOOK) {
  const l = o.light, n = Math.hypot(l[0], l[1], l[2]) || 1;
  return [l[0] / n, l[1] / n, l[2] / n];
}

/** The shade of a surface with unit normal n (view space): ambient + direct x |N.L|, x back on a back face; and the
 * factor the game multiplies a LINEAR colour by (the shade to the power gamma). Pure (for tests and checks). */
export function rawShade(n, front = true, o = RAW_LOOK) {
  const L = rawLightDir(o);
  const k = (o.ambient + o.direct * Math.abs(n[0] * L[0] + n[1] * L[1] + n[2] * L[2])) * (front ? 1 : o.back);
  return { shade: k, linear: Math.pow(k, o.gamma) };
}

/** GLSL that declares `float <name>` = the linear factor of the raw light for the fragment, from the view-space normal
 * expression `normalExpr` (or, with o.flat, the triangle's own normal from the derivatives of `viewPosExpr`). Pure. */
export function rawShadeGlsl(name = 'nsRawK', normalExpr = 'normal', viewPosExpr = 'vViewPosition', o = RAW_LOOK) {
  const L = rawLightDir(o);
  const n = o.flat ? `normalize( cross( dFdx( ${viewPosExpr} ), dFdy( ${viewPosExpr} ) ) )` : `normalize( ${normalExpr} )`;
  return `float ${name} = max( ( ${f(o.ambient)} + ${f(o.direct)} * abs( dot( ${n}, vec3( ${L.map(f).join(', ')} ) ) ) ) * ( gl_FrontFacing ? 1.0 : ${f(o.back)} ), 0.0 );\n` +
    `\t${name} = pow( ${name}, ${f(o.gamma)} );`;
}

























export const RAW_HOOKS = Object.freeze({
  ao: '#include <aomap_fragment>', normal: '#include <normal_fragment_begin>',
  lights: Object.freeze(['#include <lights_fragment_begin>', '#include <lights_fragment_maps>', '#include <lights_fragment_end>'])
});
export function patchRawShaders(vertexShader, fragmentShader, o = RAW_LOOK, opts = {}) {
  const floor = opts && Number.isFinite(opts.floor) && opts.floor > 0 ? opts.floor : 0;
  const keep = opts && Number.isFinite(opts.keep) ? Math.min(1, Math.max(0, opts.keep)) : 0, ref = opts && Number.isFinite(opts.ref) && opts.ref > 0 ? opts.ref : 1;
  if (typeof vertexShader !== 'string' || typeof fragmentShader !== 'string') return null;
  // (vViewPosition, needed only for flat normals, is declared in the lights' own pars chunk of the lambert and phong
  // shaders, so it is not in their text before the includes are resolved)
  if (!fragmentShader.includes(RAW_HOOKS.ao) || !fragmentShader.includes(RAW_HOOKS.normal) || !fragmentShader.includes('reflectedLight') ||
    fragmentShader.includes('nsRawK')) return null;
  let fs = fragmentShader;
  const hdrBoost = fragmentShader.includes('vec4 nsPu =') && fragmentShader.includes('uniform vec4 nsCharge');
  for (const h of RAW_HOOKS.lights) fs = fs.split(h).join('');
  fs = fs.replace(RAW_HOOKS.ao, `${RAW_HOOKS.ao}
	{
		${rawShadeGlsl('nsRawK', 'normal', 'vViewPosition', o)}${floor ? `
		{ // the shade floor (opts.floor): never under that luminance (opts.keep: keeping a share of the colours' ratios), a soft maximum
			${keep >= 1 ? `float nsKf = ${f(Math.min(1, floor / ref))}, nsKw = 0.5 * nsKf;`
    : keep > 0 ? `float nsKf = min( 1.0, ${f(floor / Math.pow(ref, keep))} * pow( max( dot( diffuseColor.rgb, vec3( 0.2126, 0.7152, 0.0722 ) ), 1e-4 ), ${f(keep - 1)} ) ), nsKw = 0.5 * nsKf;`
    : `float nsKf = min( 1.0, ${f(floor)} / max( dot( diffuseColor.rgb, vec3( 0.2126, 0.7152, 0.0722 ) ), 1e-4 ) ), nsKw = 0.5 * nsKf;`}
			nsRawK = min( 0.5 * ( nsRawK + nsKf + sqrt( ( nsRawK - nsKf ) * ( nsRawK - nsKf ) + nsKw * nsKw ) ), 1.0 );
		}` : ''}
		reflectedLight.directDiffuse = diffuseColor.rgb * nsRawK;
		reflectedLight.indirectDiffuse = vec3( 0.0 );
		reflectedLight.directSpecular = vec3( 0.0 );
		reflectedLight.indirectSpecular = vec3( 0.0 );
	}${hdrBoost ? `
	if ( nsCharge.z > 0.5 ) totalEmissiveRadiance *= 1.0 + nsHdrBoost.x * max( nsPu.x - nsHdrBoost.y, 0.0 );` : ''}`);
  if (hdrBoost && !/uniform\s+vec4\s+nsHdrBoost\s*;/.test(fs)) fs = 'uniform vec4 nsHdrBoost;\n' + fs;
  return { vertexShader, fragmentShader: fs, hdrBoost };
}
