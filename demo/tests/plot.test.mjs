import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeFinite,buildPlotSegments} from '../src/plot.mjs';
test('full finite numeric range has finite ordered display coordinates',()=>{
  const max=Number.MAX_VALUE;
  assert.equal(normalizeFinite(-max,-max,max),0);
  assert.equal(normalizeFinite(0,-max,max),.5);
  assert.equal(normalizeFinite(max,-max,max),1);
});
test('smallest subnormal values and constant signals remain drawable',()=>{
  assert.equal(normalizeFinite(Number.MIN_VALUE,Number.MIN_VALUE,2*Number.MIN_VALUE),0);
  assert.equal(normalizeFinite(2*Number.MIN_VALUE,Number.MIN_VALUE,2*Number.MIN_VALUE),1);
  assert.equal(normalizeFinite(0,0,0),.5);
  assert.equal(normalizeFinite(Number.MAX_VALUE,Number.MAX_VALUE,Number.MAX_VALUE),.5);
});
test('ordinary and one-ulp ranges retain endpoints',()=>{
  assert.ok(Math.abs(normalizeFinite(15,10,20)-.5)<1e-14);
  assert.equal(normalizeFinite(1,1,1+Number.EPSILON),0);
  assert.equal(normalizeFinite(1+Number.EPSILON,1,1+Number.EPSILON),1);
});
test('nonfinite and reversed ranges fail explicitly',()=>{
  assert.throws(()=>normalizeFinite(Infinity,0,1));
  assert.throws(()=>normalizeFinite(0,NaN,1));
  assert.throws(()=>normalizeFinite(1,2,1));
});
test('a null inside a display bin preserves isolated values on both sides',()=>{
  assert.deepEqual(buildPlotSegments([1,null,100],1),[[0],[2]]);
});
test('each missing-data run retains its extrema and ordered endpoints',()=>{
  const values=[0,20,5,null,-50,100,1];
  assert.deepEqual(buildPlotSegments(values,1),[[0,1,2],[4,5,6]]);
  assert.deepEqual(buildPlotSegments([2,10,1,5,4],1),[[0,1,2,4]]);
});
test('empty missing signals and invalid bin requests are explicit',()=>{
  assert.deepEqual(buildPlotSegments([null,null],1),[]);
  assert.deepEqual(buildPlotSegments([],1),[]);
  assert.throws(()=>buildPlotSegments([1],0));
  assert.throws(()=>buildPlotSegments([NaN],1));
});
