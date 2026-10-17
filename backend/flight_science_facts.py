"""Planet-specific science questions; choices are shuffled at game start.

References: https://science.nasa.gov/solar-system/planets/ and individual NASA
planet-facts pages. Each item has 3 distinct choices and one correct choice.
"""

def q(question, correct, wrong_a, wrong_b, explanation):
    return dict(question=question,correct=correct,choices=(correct,wrong_a,wrong_b),explanation=explanation)

SCIENCE_QUESTIONS={
 'MERCURY':[
  q('Which planet is closest to the Sun?', 'Mercury','Venus','Mars','Mercury is the innermost planet.'),
  q('How long is a Mercury year?', '88 Earth days','365 Earth days','12 Earth years','Mercury completes an orbit around the Sun in 88 Earth days.'),
  q('What may hide in Mercury’s shadowed polar craters?', 'Water ice','Liquid methane','Rainforests','Some permanently shaded craters contain water ice.'),
  q('Why does Mercury have extreme temperature swings?', 'Almost no atmosphere','An ocean covering it','Thick cloud insulation','Mercury has very little atmosphere to retain heat.'),
  q('Mercury is mostly a…', 'Rocky planet','Gas giant','Star','Mercury has a rocky surface and metallic core.')],
 'VENUS':[
  q('Which planet has the hottest surface?', 'Venus','Mercury','Mars','A thick atmosphere traps heat on Venus.'),
  q('What causes the intense heating on Venus?', 'Greenhouse effect','Volcanic ice','Solar eclipses','Carbon dioxide traps outgoing heat.'),
  q('Venus rotates…', 'Opposite most planets','Only once per hour','Around Earth','Venus has retrograde rotation.'),
  q('Venus’s clouds contain droplets of…', 'Sulfuric acid','Fresh water','Liquid nitrogen','Venus has corrosive sulfuric-acid clouds.'),
  q('Which describes the surface of Venus?', 'Hot and rocky','Frozen ocean','Liquid hydrogen','Venus is a rocky terrestrial planet with extreme heat.')],
 'EARTH':[
  q('Which planet has known liquid oceans on its surface?', 'Earth','Jupiter','Venus','Earth has extensive oceans of liquid water.'),
  q('How many natural moons does Earth have?', 'One','Four','Zero','Earth has one natural Moon.'),
  q('What helps shield Earth from solar charged particles?', 'Magnetic field','Its rings','A giant ice shell','Earth’s magnetosphere deflects many charged particles.'),
  q('About how long does Earth take to orbit the Sun?', 'One year','88 days','12 years','An Earth year is one solar orbit.'),
  q('Which layer contains most of Earth’s weather?', 'Troposphere','Core','Mantle','Most weather occurs in the lower atmosphere.')],
 'MARS':[
  q('What gives Mars its rusty red appearance?', 'Iron oxides','Green plants','Liquid sulfur','Oxidized iron minerals color Martian dust.'),
  q('How many natural moons does Mars have?', 'Two','One','Seven','Mars has Phobos and Deimos.'),
  q('What is Olympus Mons?', 'A huge volcano','An ocean','An orbiting telescope','Olympus Mons is a giant Martian volcano.'),
  q('Mars’s atmosphere is mostly…', 'Carbon dioxide','Oxygen','Hydrogen','Carbon dioxide dominates the thin Martian atmosphere.'),
  q('What can cover large areas of Mars?', 'Dust storms','Liquid rain oceans','Saturn-like rings','Martian dust storms can spread around the planet.')],
 'JUPITER':[
  q('Jupiter is the solar system’s…', 'Largest planet','Hottest planet','Smallest planet','Jupiter is the largest planet.'),
  q('What is Jupiter’s Great Red Spot?', 'Giant storm','Solid island','Volcano','The Great Red Spot is an enormous storm.'),
  q('Jupiter is mainly composed of…', 'Hydrogen and helium','Granite and soil','Liquid iron','Jupiter is a gas giant rich in hydrogen and helium.'),
  q('Which moon likely hides a salty ocean?', 'Europa','Phobos','Titan','Evidence suggests Europa has an ocean beneath its icy crust.'),
  q('Which Jovian moon has many active volcanoes?', 'Io','Earth’s Moon','Triton','Io is exceptionally volcanically active.')],
 'SATURN':[
  q('Saturn’s rings mostly contain…', 'Ice and rock','Liquid lava','Air and leaves','The rings are made from countless pieces of ice and rock.'),
  q('What kind of planet is Saturn?', 'Gas giant','Rocky planet','Dwarf planet','Saturn is a gas giant without a solid surface.'),
  q('Which large Saturn moon has methane lakes?', 'Titan','Europa','Phobos','Titan has methane-and-ethane lakes and seas.'),
  q('Which planet is famous for its broad bright rings?', 'Saturn','Mercury','Venus','Saturn’s extensive rings are easy to recognize.'),
  q('Where do Saturn’s rings orbit?', 'Around Saturn','Around the Sun alone','Around Earth','The ring particles orbit Saturn under its gravity.')],
 'URANUS':[
  q('What makes Uranus’s rotation unusual?', 'It spins almost on its side','It never spins','It spins around Earth','Uranus’s axis is tilted about 98 degrees.'),
  q('Which gas helps give Uranus a blue-green tint?', 'Methane','Carbon monoxide','Oxygen','Atmospheric methane absorbs red light.'),
  q('About how long is a Uranus year?', '84 Earth years','88 days','One month','Uranus takes about 84 Earth years to orbit the Sun.'),
  q('Uranus is classified as an…', 'Ice giant','Star','Asteroid','Uranus is an ice giant.'),
  q('Does Uranus have rings?', 'Yes','No','Only one solid ring','Uranus has a system of dark, faint rings.')],
 'NEPTUNE':[
  q('Which is the farthest planet from the Sun?', 'Neptune','Uranus','Mars','Neptune is the eighth and farthest recognized planet.'),
  q('Neptune is known for…', 'Extremely fast winds','Surface forests','Liquid lava oceans','Neptune has extremely fast atmospheric winds.'),
  q('Which large moon orbits Neptune backwards?', 'Triton','Titan','Io','Triton has a retrograde orbit.'),
  q('What type of planet is Neptune?', 'Ice giant','Rocky planet','Dwarf planet','Neptune is classified as an ice giant.'),
  q('What gas contributes to Neptune’s blue appearance?', 'Methane','Chlorine','Sulfur dioxide','Methane absorbs red sunlight in Neptune’s atmosphere.')]
}
