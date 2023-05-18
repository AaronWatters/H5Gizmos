
import {
    chordDiagram
} from './chart.js';

window.append_chord_diagram = function(target, array2d, names, colors) {
    const data = Object.assign(
        array2d,
        {
            names: names,
            colors: colors,
        },
    );
    const chart = chordDiagram(data);
    // assume target is a jQuery container.
    target[0].append(chart);
};
