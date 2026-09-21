const assert=require('node:assert/strict');
const {timing,split}=require('../static/editor-timeline.js');
assert.deepEqual(timing({mbStart:-1,mbDuration:2}),{start:0,duration:2,offset:0});
assert.equal(split({mbStart:2,mbDuration:4},1),null);
assert.equal(split({mbStart:2,mbDuration:4},2.1),null);
assert.deepEqual(split({mbStart:2,mbDuration:4,mbMediaOffset:3},4),{left:2,right:2,start:4,offset:5});
assert.equal(split({mbStart:2,mbDuration:4},6),null);
console.log('PASS: timeline defaults, split boundaries, video source offset');
