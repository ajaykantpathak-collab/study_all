"""
NCERT chapter index for CBSE-aligned chapter picker.
Chapters follow standard NCERT textbook naming (Classes 1–12).
"""

from __future__ import annotations

CHAPTER_ANY = "— Any chapter / Full book —"

# class -> subject -> [chapters]
NCERT_SYLLABUS: dict[str, dict[str, list[str]]] = {
    "1": {
        "Mathematics": [
            "Shapes and Space", "Numbers from One to Nine", "Addition", "Subtraction",
            "Numbers from Ten to Twenty", "Time", "Measurement", "Data Handling",
            "Patterns", "Numbers from Twenty-one to Fifty", "Money", "How Many",
        ],
        "English": ["A Happy Child", "After a Bath", "One Little Kitten", "Lalu and Peelu"],
        "Hindi": ["झूला", "आम की कहानी", "पत्ते", "पकौड़ी"],
        "EVS / Science": ["About Me", "My Family", "Food", "Water", "Plants", "Animals"],
    },
    "2": {
        "Mathematics": [
            "What is Long, What is Round?", "Counting in Groups", "How Much Can You Carry?",
            "Counting in Tens", "Patterns", "Footprints", "Jugs and Mugs",
            "Tens and Ones", "My Funday", "Add Our Points", "Lines and Lines",
        ],
        "English": ["First Day at School", "Haldis Adventure", "Paddling-Pool", "I am Lucky"],
        "Hindi": ["ऊँट चला", "मीठी सारंगी", "चूहो! म्याऊँ सो रही है"],
        "EVS / Science": ["Growing Plants", "Our Houses", "Air", "Water", "Animals"],
    },
    "3": {
        "Mathematics": [
            "Where to Look From", "Fun with Numbers", "Give and Take", "Long and Short",
            "Shapes and Designs", "Fun with Give and Take", "Time Goes On",
            "Who is Heavier?", "How Many Times?", "Play with Patterns", "Jugs and Mugs",
        ],
        "English": ["Good Morning", "The Magic Garden", "Bird Talk", "Nina and the Sparrows"],
        "Hindi": ["कक्कू", "कहीं नहीं", "टोपी", "मन करता है"],
        "EVS / Science": ["Family and Friends", "Food and Feeding", "Shelter", "Water O Water"],
    },
    "4": {
        "Mathematics": [
            "Building with Bricks", "Long and Short", "A Trip to Bhopal", "Tick-Tick-Tick",
            "The Way the World Looks", "The Junk Seller", "Jugs and Mugs",
            "Carts and Wheels", "Halves and Quarters", "Play with Patterns",
        ],
        "English": ["Wake Up!", "Nehas Alarm Clock", "Noses", "The Little Fir Tree"],
        "Hindi": ["मन के भोले-भाले बादल", "जैसा सवाल वैसा जवाब", "पापा जब बच्चे थे"],
        "EVS / Science": ["Going to School", "Ear to Ear", "A Day with Nandita", "Food and Digestion"],
    },
    "5": {
        "Mathematics": [
            "The Fish Tale", "Shapes and Angles", "How Many Squares?", "Parts and Wholes",
            "Does it Look the Same?", "Be My Multiple, I'll be Your Factor",
            "Can You See the Pattern?", "Mapping Your Way", "Boxes and Sketches",
        ],
        "English": ["Ice-cream Man", "Teamwork", "Flying Together", "My Shadow"],
        "Hindi": ["राख की रस्म", "फसलों के त्योहार", "खिलौनेवाला"],
        "EVS / Science": ["Super Senses", "A Snake Charmer's Story", "Seeds and Seeds", "Water"],
    },
    "6": {
        "Mathematics": [
            "Knowing Our Numbers", "Whole Numbers", "Playing with Numbers", "Basic Geometrical Ideas",
            "Understanding Elementary Shapes", "Integers", "Fractions", "Decimals",
            "Data Handling", "Mensuration", "Algebra", "Ratio and Proportion", "Symmetry",
        ],
        "Science": [
            "Food: Where Does It Come From?", "Components of Food", "Fibre to Fabric",
            "Sorting Materials into Groups", "Separation of Substances", "Changes Around Us",
            "Getting to Know Plants", "Body Movements", "The Living Organisms",
            "Motion and Measurement of Distances", "Light, Shadows and Reflections",
            "Electricity and Circuits", "Fun with Magnets", "Water", "Air Around Us",
        ],
        "Social Science": [
            "What, Where, How and When?", "From Hunting-Gathering to Growing Food",
            "In the Earliest Cities", "What Books and Burials Tell Us",
            "Kingdoms, Kings and Early Republic", "New Questions and Ideas",
            "Ashoka, The Emperor", "Villages, Towns and Trade", "New Empires and Kingdoms",
        ],
        "English": ["Who Did Patrick's Homework?", "How the Dog Found Himself", "Taro's Reward"],
        "Hindi": ["वह चिड़िया जो", "बचपन", "नादान दोस्त"],
    },
    "7": {
        "Mathematics": [
            "Integers", "Fractions and Decimals", "Data Handling", "Simple Equations",
            "Lines and Angles", "The Triangle and its Properties", "Comparing Quantities",
            "Rational Numbers", "Perimeter and Area", "Algebraic Expressions",
            "Exponents and Powers", "Symmetry", "Visualising Solid Shapes",
        ],
        "Science": [
            "Nutrition in Plants", "Nutrition in Animals", "Fibre to Fabric", "Heat",
            "Acids, Bases and Salts", "Physical and Chemical Changes", "Weather, Climate and Adaptations",
            "Winds, Storms and Cyclones", "Soil", "Respiration in Organisms",
            "Transportation in Animals and Plants", "Reproduction in Plants", "Motion and Time",
            "Electric Current and its Effects", "Light", "Water: A Precious Resource",
        ],
        "Social Science": [
            "Tracing Changes Through a Thousand Years", "New Kings and Kingdoms",
            "The Delhi Sultans", "The Mughal Empire", "Rulers and Buildings",
            "Towns, Traders and Craftspersons", "Tribes, Nomads and Settled Communities",
        ],
        "English": ["Three Questions", "A Gift of Chappals", "Gopal and the Hilsa Fish"],
        "Hindi": ["हम पंछी उन्मुक्त गगन के", "दादी माँ", "हिमालय की बेटियाँ"],
    },
    "8": {
        "Mathematics": [
            "Rational Numbers", "Linear Equations in One Variable", "Understanding Quadrilaterals",
            "Practical Geometry", "Data Handling", "Squares and Square Roots", "Cubes and Cube Roots",
            "Comparing Quantities", "Algebraic Expressions and Identities", "Visualising Solid Shapes",
            "Mensuration", "Exponents and Powers", "Direct and Inverse Proportions",
            "Factorisation", "Introduction to Graphs",
        ],
        "Science": [
            "Crop Production and Management", "Microorganisms: Friend and Foe",
            "Synthetic Fibres and Plastics", "Materials: Metals and Non-Metals",
            "Coal and Petroleum", "Combustion and Flame", "Conservation of Plants and Animals",
            "Cell — Structure and Functions", "Reproduction in Animals",
            "Reaching the Age of Adolescence", "Force and Pressure", "Friction",
            "Sound", "Chemical Effects of Electric Current", "Some Natural Phenomena",
            "Light", "Stars and the Solar System", "Pollution of Air and Water",
        ],
        "Social Science": [
            "How, When and Where", "From Trade to Territory", "Ruling the Countryside",
            "Tribals, Dikus and the Vision of a Golden Age", "When People Rebel",
            "Colonialism and the City", "Weavers, Iron Smelters and Factory Owners",
        ],
        "English": ["The Best Christmas Present in the World", "The Tsunami", "Glimpses of the Past"],
        "Hindi": ["ध्वनि", "लाख की चूड़ियाँ", "बस की यात्रा"],
    },
    "9": {
        "Mathematics": [
            "Number Systems", "Polynomials", "Coordinate Geometry", "Linear Equations in Two Variables",
            "Introduction to Euclid's Geometry", "Lines and Angles", "Triangles",
            "Quadrilaterals", "Circles", "Heron's Formula", "Surface Areas and Volumes", "Statistics",
        ],
        "Science": [
            "Matter in Our Surroundings", "Is Matter Around Us Pure?", "Atoms and Molecules",
            "Structure of the Atom", "The Fundamental Unit of Life", "Tissues",
            "Motion", "Force and Laws of Motion", "Gravitation", "Work and Energy", "Sound",
            "Why Do We Fall Ill?", "Natural Resources", "Improvement in Food Resources",
        ],
        "Social Science": [
            "The French Revolution", "Socialism in Europe and the Russian Revolution",
            "Nazism and the Rise of Hitler", "Forest Society and Colonialism",
            "Physical Features of India", "Drainage", "Climate", "Natural Vegetation and Wildlife",
            "Population", "What is Democracy? Why Democracy?", "Constitutional Design",
        ],
        "English": ["The Fun They Had", "The Sound of Music", "The Little Girl", "A Truly Beautiful Mind"],
        "Hindi": ["दो बैलों की कथा", "ल्हासा की ओर", "उपभोक्तावाद की संस्कृति"],
    },
    "10": {
        "Mathematics": [
            "Real Numbers", "Polynomials", "Pair of Linear Equations in Two Variables",
            "Quadratic Equations", "Arithmetic Progressions", "Triangles", "Coordinate Geometry",
            "Introduction to Trigonometry", "Applications of Trigonometry", "Circles",
            "Areas Related to Circles", "Surface Areas and Volumes", "Statistics", "Probability",
        ],
        "Science": [
            "Chemical Reactions and Equations", "Acids, Bases and Salts", "Metals and Non-metals",
            "Carbon and its Compounds", "Life Processes", "Control and Coordination",
            "How do Organisms Reproduce?", "Heredity and Evolution", "Light — Reflection and Refraction",
            "The Human Eye and the Colourful World", "Electricity", "Magnetic Effects of Electric Current",
        ],
        "Social Science": [
            "The Rise of Nationalism in Europe", "Nationalism in India",
            "Resources and Development", "Forest and Wildlife Resources", "Water Resources",
            "Agriculture", "Minerals and Energy Resources", "Manufacturing Industries",
            "Power Sharing", "Federalism", "Democracy and Diversity",
        ],
        "English": ["A Letter to God", "Nelson Mandela: Long Walk to Freedom", "Two Stories about Flying"],
        "Hindi": ["सूरदास के पद", "राम-लक्ष्मण-परशुराम संवाद", "सवैया और कवित्त"],
    },
    "11": {
        "Physics": [
            "Physical World", "Units and Measurements", "Motion in a Straight Line",
            "Motion in a Plane", "Laws of Motion", "Work, Energy and Power",
            "System of Particles and Rotational Motion", "Gravitation", "Mechanical Properties of Solids",
            "Mechanical Properties of Fluids", "Thermal Properties of Matter", "Thermodynamics",
            "Kinetic Theory", "Oscillations", "Waves",
        ],
        "Chemistry": [
            "Some Basic Concepts of Chemistry", "Structure of Atom", "Classification of Elements",
            "Chemical Bonding and Molecular Structure", "Thermodynamics", "Equilibrium",
            "Redox Reactions", "Organic Chemistry — Basic Principles", "Hydrocarbons", "Environmental Chemistry",
        ],
        "Mathematics": [
            "Sets", "Relations and Functions", "Trigonometric Functions", "Complex Numbers",
            "Linear Inequalities", "Permutations and Combinations", "Binomial Theorem",
            "Sequences and Series", "Straight Lines", "Conic Sections", "Introduction to Three Dimensional Geometry",
            "Limits and Derivatives", "Statistics", "Probability",
        ],
        "Biology": [
            "The Living World", "Biological Classification", "Plant Kingdom", "Animal Kingdom",
            "Morphology of Flowering Plants", "Anatomy of Flowering Plants", "Structural Organisation in Animals",
            "Cell: The Unit of Life", "Biomolecules", "Cell Cycle and Cell Division",
            "Photosynthesis in Higher Plants", "Respiration in Plants", "Plant Growth and Development",
        ],
        "Accountancy": [
            "Introduction to Accounting", "Theory Base of Accounting", "Recording of Transactions — I",
            "Recording of Transactions — II", "Bank Reconciliation Statement", "Trial Balance and Rectification",
            "Depreciation, Provisions and Reserves", "Bill of Exchange",
        ],
        "Economics": [
            "Introduction", "Collection of Data", "Organisation of Data", "Presentation of Data",
            "Measures of Central Tendency", "Measures of Dispersion", "Correlation", "Index Numbers",
        ],
    },
    "12": {
        "Physics": [
            "Electric Charges and Fields", "Electrostatic Potential and Capacitance", "Current Electricity",
            "Moving Charges and Magnetism", "Magnetism and Matter", "Electromagnetic Induction",
            "Alternating Current", "Electromagnetic Waves", "Ray Optics and Optical Instruments",
            "Wave Optics", "Dual Nature of Radiation and Matter", "Atoms", "Nuclei",
            "Semiconductor Electronics", "Communication Systems",
        ],
        "Chemistry": [
            "The Solid State", "Solutions", "Electrochemistry", "Chemical Kinetics",
            "Surface Chemistry", "General Principles and Processes of Isolation of Elements",
            "The p-Block Elements", "The d- and f-Block Elements", "Coordination Compounds",
            "Haloalkanes and Haloarenes", "Alcohols, Phenols and Ethers", "Aldehydes, Ketones and Carboxylic Acids",
            "Amines", "Biomolecules", "Polymers", "Chemistry in Everyday Life",
        ],
        "Mathematics": [
            "Relations and Functions", "Inverse Trigonometric Functions", "Matrices", "Determinants",
            "Continuity and Differentiability", "Application of Derivatives", "Integrals",
            "Application of Integrals", "Differential Equations", "Vector Algebra",
            "Three Dimensional Geometry", "Linear Programming", "Probability",
        ],
        "Biology": [
            "Reproduction in Organisms", "Sexual Reproduction in Flowering Plants", "Human Reproduction",
            "Reproductive Health", "Principles of Inheritance and Variation", "Molecular Basis of Inheritance",
            "Evolution", "Human Health and Disease", "Microbes in Human Welfare",
            "Biotechnology: Principles and Processes", "Biotechnology and its Applications",
            "Organisms and Populations", "Ecosystem", "Biodiversity and Conservation",
        ],
        "Accountancy": [
            "Accounting for Partnership: Basic Concepts", "Reconstitution of a Partnership Firm",
            "Admission of a Partner", "Retirement/Death of a Partner", "Dissolution of Partnership Firm",
            "Accounting for Share Capital", "Issue and Redemption of Debentures", "Financial Statements of a Company",
        ],
    },
}

# Map app subject names → NCERT book keys
SUBJECT_ALIASES: dict[str, str] = {
    "EVS / Science": "EVS / Science",
    "Science": "Science",
    "Social Studies": "Social Science",
    "Social Science": "Social Science",
    "Informatics Practices": "Computer Science",
    "Information Technology": "Computer Science",
}


def ncert_subjects_for_class(class_num: str) -> list[str]:
    books = NCERT_SYLLABUS.get(class_num, {})
    return sorted(books.keys())


def ncert_chapters_for(class_num: str, subject: str) -> list[str]:
    if not subject:
        return [CHAPTER_ANY]
    books = NCERT_SYLLABUS.get(class_num, {})
    key = SUBJECT_ALIASES.get(subject, subject)
    chapters = books.get(key) or books.get(subject) or []
    if not chapters:
        return [CHAPTER_ANY]
    return [CHAPTER_ANY] + chapters


def chapter_available(class_num: str, subject: str) -> bool:
    books = NCERT_SYLLABUS.get(class_num, {})
    key = SUBJECT_ALIASES.get(subject, subject)
    return bool(books.get(key) or books.get(subject))
