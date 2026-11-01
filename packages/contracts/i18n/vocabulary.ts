/**
 * Central Internationalization & Djinn Vocabulary Dictionary.
 * Strict Safety Invariant:
 * Legal consent, refusal reasons, and deterministic eligibility explanations
 * ALWAYS remain in literal, plain language. Djinn wording is reserved for
 * titles, summon buttons, agent working states, and celebration headers.
 */

export const DJINN_WISH_TYPES = {
  FOUNDATION_WISH: {
    id: 'FOUNDATION_WISH',
    name: 'Foundation Wish',
    product: 'Home Loan',
    requiredDocs: ['PAN', 'AADHAAR_MASKED', 'SALARY_SLIP', 'BANK_STATEMENT', 'TITLE_DEED', 'EC'],
  },
  SCHOLAR_WISH: {
    id: 'SCHOLAR_WISH',
    name: 'Scholar Wish',
    product: 'Education Loan',
    requiredDocs: ['PAN', 'AADHAAR_MASKED', 'MARKSHEET', 'SALARY_SLIP'],
  },
  OPPORTUNITY_WISH: {
    id: 'OPPORTUNITY_WISH',
    name: 'Opportunity Wish',
    product: 'Personal Loan',
    requiredDocs: ['PAN', 'AADHAAR_MASKED', 'SALARY_SLIP'],
  },
  GROWTH_WISH: {
    id: 'GROWTH_WISH',
    name: 'Growth Wish',
    product: 'Business Loan',
    requiredDocs: ['PAN', 'AADHAAR_MASKED', 'BANK_STATEMENT', 'ITR', 'FORM16'],
  },
} as const;

export const VOCABULARY = {
  en: {
    summonButton: 'SUMMON YOUR DJINN',
    workingState: 'Djinn is working...',
    wishGranted: 'Your wish is granted',
    poweredBy: 'Powered by Djinn',
    createWishLink: 'Create your own wish',
    sections: {
      s01: '01 WISH',
      s02: '02 DOCUMENTS',
      s03: '03 CHECKS',
      s04: '04 DEPARTMENTS',
      s05: '05 VERDICT',
    },
    stepper: {
      s1: 'Summoned',
      s2: 'Documents',
      s3: 'Checks',
      s4: 'Review',
      s5: 'Granted',
    },
    // Literal legal & consent copy - Zero Djinn slang
    legal: {
      consentHeading: 'Consent Specification & Regulatory Notice',
      consentWarning: 'You are consenting to share encrypted document slices with the lending bank for underwriting under the Digital Personal Data Protection Act (DPDPA).',
      rejectionPrefix: 'Application review concluded. Eligibility requirements not satisfied according to deterministic underwriting criteria.',
    },
  },
  hi: {
    summonButton: 'अपने जिन को बुलाएं',
    workingState: 'जिन कार्य कर रहा है...',
    wishGranted: 'आपकी मुराद पूरी हुई',
    poweredBy: 'जिन द्वारा संचालित',
    createWishLink: 'अपनी मुराद बनाएं',
    sections: {
      s01: '01 मुराद',
      s02: '02 दस्तावेज',
      s03: '03 सत्यापन',
      s04: '04 विभाग',
      s05: '05 फैसला',
    },
    stepper: {
      s1: 'आरंभ',
      s2: 'दस्तावेज',
      s3: 'जांच',
      s4: 'समीक्षा',
      s5: 'स्वीकृत',
    },
    legal: {
      consentHeading: 'सहमति विनिर्देश और विनियामक सूचना',
      consentWarning: 'आप डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम (DPDPA) के तहत बैंक के साथ सत्यापित दस्तावेज साझा करने की सहमति दे रहे हैं।',
      rejectionPrefix: 'आवेदन की समीक्षा समाप्त हुई। ऋण पात्रता मानदंडों को पूरा नहीं किया गया है।',
    },
  },
  hinglish: {
    summonButton: 'APNA DJINN BULAYEIN',
    workingState: 'Djinn kaam kar raha hai...',
    wishGranted: 'Aapki wish grant ho chuki hai',
    poweredBy: 'Powered by Djinn',
    createWishLink: 'Apni wish create karein',
    sections: {
      s01: '01 WISH',
      s02: '02 DOCUMENTS',
      s03: '03 CHECKS',
      s04: '04 DEPARTMENTS',
      s05: '05 VERDICT',
    },
    stepper: {
      s1: 'Summoned',
      s2: 'Documents',
      s3: 'Checks',
      s4: 'Review',
      s5: 'Granted',
    },
    legal: {
      consentHeading: 'Consent Specification & Regulatory Notice',
      consentWarning: 'Aap DPDPA act ke mutabiq lending bank ke saath documents share karne ki consent de rahe hain.',
      rejectionPrefix: 'Application evaluate ho gayi hai. Underwriting criteria satisfy nahi hua.',
    },
  },
} as const;

export type SupportedLanguage = keyof typeof VOCABULARY;
